"""Describe static menu references without selecting a runnable program.

Original observations and issue codes remain in the source manifest. Recognized
patterns close only the task of explaining differing paths, never runtime QA.
"""
from pathlib import PurePosixPath


def _path(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        return None
    value = value.replace('\\', '/')
    if value.startswith('/') or ':' in value or '..' in value.split('/'):
        return None
    return str(PurePosixPath(value)).casefold()


def explain_references(entry):
    evidence = entry.get('evidence', {})
    references = entry.get('files', {}).get('referenced', {})
    present = {_path(f.get('path')) for f in references.values()
               if f.get('exists') is True and f.get('sha256') and f.get('size', 0) > 0}
    present.discard(None)
    absent = {_path(f.get('path')) for f in references.values() if f.get('exists') is False}
    absent.discard(None)
    issues = set(entry.get('issues', []))
    allowed = {'conflicting_launch_targets', 'missing_launch_file'}
    if not present or present & absent or not issues or issues - allowed:
        return None

    launches = evidence.get('launches', {})
    direct = launches.get('direct', [])
    warning = launches.get('warning_continue', [])
    def paths(rows):
        return [_path(row.get('file', {}).get('path')) for row in rows]
    d, w = paths(direct), paths(warning)
    # Every path must be accounted for. No name similarity or cross-CD reuse.
    if d and w and all(d + w) and set(d + w) == present | absent:
        if set(d) <= absent and set(w) == present:
            return {'pattern': 'missing_alternative_references',
                    'explanation': 'Direkteknappen refererer til manglende filer. Fortsett-knappen refererer til filer registrert på samme CD.'}
        # A common target plus additional calls in the SAME source handler is
        # a multi-file observation, not proof of mutually exclusive programs.
        locations = {(r.get('frame'), r.get('channel'), r.get('library'),
                      r.get('member'), r.get('script_resource'),
                      r.get('handler', {}).get('cp1252_view')) for r in warning}
        if (not absent and set(d) < set(w) == present and len(locations) == 1
                and all(x is not None for x in next(iter(locations)))
                and len({r.get('offset') for r in warning}) == len(warning)
                and all(isinstance(r.get('offset'), int) for r in warning)):
            return {'pattern': 'multiple_files_in_same_handler',
                    'explanation': 'Fortsett-skriptet refererer til flere filer, inkludert direkteknappens mål. Alle er registrert på CD-en. Kjørerekkefølge og installasjon er ikke bekreftet.'}

    primary = evidence.get('primary_launch', {}).get('path')
    continuation = evidence.get('warning_continue', {}).get('path')
    # Recognize a damaged literal only when the remainder equals the other
    # original reference exactly (apart from Windows path case). Never rewrite it.
    if isinstance(primary, str):
        stripped = primary.rstrip(''.join(chr(i) for i in range(32)))
        if (stripped != primary and _path(stripped) is not None
                and _path(stripped) == _path(continuation)
                and present == {_path(continuation)} and not absent
                and issues == allowed):
            return {'pattern': 'trailing_control_characters',
                    'explanation': 'Direkteknappens filnavn har avsluttende kontrolltegn. Fortsett-knappens tilsvarende filnavn er registrert på CD-en. Originalstrengen er bevart.'}
    return None
