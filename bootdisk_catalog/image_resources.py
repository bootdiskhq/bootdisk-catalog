"""Bounded verification of compressed Director resource observations."""
import zlib

def require(condition, message):
    if not condition: raise ValueError(message)


def resource_slice(container, resource):
    """Verify a raw or explicitly zlib-compressed slice of preserved media."""
    offset=resource.get('offset'); size=resource.get('size')
    require(type(offset) is int and offset>=0 and type(size) is int and size>=0, 'invalid resource slice')
    if 'compression' not in resource:
        require(offset+size<=len(container), 'resource slice outside container')
        return container[offset:offset+size]
    require(resource['compression']=='zlib', 'unsupported resource compression')
    compressed=resource.get('compressed_size'); expanded=resource.get('expanded_size'); start=resource.get('payload_offset')
    require(type(compressed) is int and compressed>0 and offset+compressed<=len(container), 'compressed slice outside container')
    require(type(expanded) is int and 0<=expanded<=128*1024*1024 and type(start) is int and start>=0 and start+size<=expanded, 'invalid expanded slice')
    obj=zlib.decompressobj()
    try:
        data=obj.decompress(container[offset:offset+compressed],expanded+1)
    except zlib.error as error:
        raise ValueError('invalid compressed resource') from error
    require(len(data)==expanded and obj.eof and not obj.unused_data and not obj.unconsumed_tail, 'compressed resource length mismatch')
    return data[start:start+size]


