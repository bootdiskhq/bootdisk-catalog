# ADR 011: Katalogfør kilden uavhengig av programidentitet

Vedtak 2026-10-15, etter Stians godkjenning av kildebasert automatisk katalogføring.

Den tidligere førstegjennomgangen krevde analyse av programfil, versjon og utgave
for nesten hver ny post. Dette blander to spørsmål: hva CD-en presenterer, og hva
en installasjonsfil faktisk inneholder. Flere titalls CD-er kan ikke gi hundrevis
av obligatoriske manuelle godkjenninger hver.

Katalogen får derfor en separat, deterministisk `source_catalog`-vurdering.
`documented` betyr at navnet er knyttet til et konkret bevart kildefelt.
Director-tekst kontrolleres mot de bevarte base64-bytene og tekstrepresentasjonen;
menynavn kan normaliseres for mellomrom. Verkstedhyllens første linje er navnet.
DTX-navn kontrolleres mot seksjonen; Tools bruker den eksisterende kontrollen av
bevarte DTX-byter, hash, inventar og seksjon. Beskrivelsen kommer uendret gjennom
`source_context`. Manglende beskrivelse er tillatt, ikke erstattet av ny tekst.

Dette lager ingen software-, release- eller identification-poster. Eksisterende
produktidentifikasjoner, versjoner, menneskevedtak og kladder berøres ikke.
Versjon og utgave er frivillig berikelse, ikke krav for å katalogføre en kildepost.
Et navn i CD-menyen beviser ikke hvilken programversjon en fil inneholder.

Filkobling vurderes separat: observed, conflict, needs_inspection, missing,
not_runtime_tested eller not_applicable_or_unrecorded. `observed` betyr en
manifestobservasjon, ikke en ny lesing eller kjøring av programfilen. Konflikter
og ukjente avvik beholdes som maskinoppgaver. Ukjente avvik stopper automatisk
ferdigstilling. Manglende fil og ikke-testet menyatferd forblir eksplisitte avvik.
Ingen av disse blir automatisk en menneskeoppgave uten et konkret spørsmål.

`presentation_projection` inkluderer vurderingen ved hver ordinære databygging.
Den kan også kjøres direkte med `python -m bootdisk_catalog.source_readiness MANIFEST`.
Tidligere `first_pass` og ReviewWorkspace-kontrakter endres ikke i denne PR-en;
deres produktidentifikasjonskø må ikke brukes som mål på katalogrestanse.

## Akseptanse og videre arbeid

På de 194 tidligere uidentifiserte postene fra rc15 er alle 194 kildenavn bundet.
169 har observerte filreferanser, 9 har konflikter, 1 trenger videre filanalyse,
2 har manglende startfiler, 12 har ikke-testet felles menykontroll og 1 har ingen
registrert ekstern startfil. Ti maskinoppgaver gjenstår; null menneskespørsmål er
opprettet. Det betyr ikke at de ti maskinoppgavene er løst eller at alle filer
er bekreftet. Historiske programmer kjøres ikke.

Neste maskinrunde skal undersøke disse ti konkrete koblingene, bevare kjente
kildeavvik og først formulere et menneskespørsmål dersom CD-kildene ikke avgjør
saken. Før nye CD-er tas inn skal samme vurdering følge ordinær projeksjon og
rapportere kildekatalog, filavvik og valgfri berikelse separat.
