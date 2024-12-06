import struct
from dataclasses import dataclass, field
from typing import Any

from pyipp.enums import IppTag, IppStatus, IppOperation
from pyipp.tags import ATTRIBUTE_TAG_MAP

from . import parser

"""
https://www.rfc-editor.org/rfc/rfc8010.html#section-3.1.1
"""

ATTRIBUTE_TAG_MAP['charset'] = IppTag.CHARSET
ATTRIBUTE_TAG_MAP['charset-configured'] = IppTag.CHARSET
ATTRIBUTE_TAG_MAP['compression-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['document-format-default'] = IppTag.MIME_TYPE
ATTRIBUTE_TAG_MAP['document-format-supported'] = IppTag.MIME_TYPE
ATTRIBUTE_TAG_MAP['generated-natural-language-supported'] = IppTag.LANGUAGE
ATTRIBUTE_TAG_MAP['ipp-versions-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['job-creation-attributes-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['job-settable-attributes-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['media-col-database'] = IppTag.BEGIN_COLLECTION
ATTRIBUTE_TAG_MAP['media-col-ready'] = IppTag.BEGIN_COLLECTION
ATTRIBUTE_TAG_MAP['media-col'] = IppTag.BEGIN_COLLECTION
ATTRIBUTE_TAG_MAP['media-col-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['media-ready'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['multiple-document-handling-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['page-delivery-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['pdf-versions-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['print-scaling-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['printer-get-attributes-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['natural-language'] = IppTag.LANGUAGE
ATTRIBUTE_TAG_MAP['pdl-override'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['printer-make-and-model'] = IppTag.TEXT
ATTRIBUTE_TAG_MAP['printer-name'] = IppTag.NAME
ATTRIBUTE_TAG_MAP['printer-dns-sd-name'] = IppTag.NAME
ATTRIBUTE_TAG_MAP['uri-authentication-supported'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['uri-security-supported'] = IppTag.KEYWORD

ATTRIBUTE_TAG_MAP['status-message'] = IppTag.TEXT
ATTRIBUTE_TAG_MAP['detailed-status-message'] = IppTag.TEXT
ATTRIBUTE_TAG_MAP['document-access-error'] = IppTag.TEXT
ATTRIBUTE_TAG_MAP['job-state-message'] = IppTag.TEXT
ATTRIBUTE_TAG_MAP['output-device-assigned'] = IppTag.NAME
ATTRIBUTE_TAG_MAP['job-message-from-operator'] = IppTag.TEXT
ATTRIBUTE_TAG_MAP['printer-state-message'] = IppTag.TEXT
ATTRIBUTE_TAG_MAP['media'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['printer-resolution'] = IppTag.RESOLUTION
ATTRIBUTE_TAG_MAP['sides'] = IppTag.KEYWORD

ATTRIBUTE_TAG_MAP['ColorModel'] = IppTag.NAME
ATTRIBUTE_TAG_MAP['Duplex'] = IppTag.NAME
ATTRIBUTE_TAG_MAP['Resolution'] = IppTag.NAME
ATTRIBUTE_TAG_MAP['output-bin'] = IppTag.KEYWORD
ATTRIBUTE_TAG_MAP['output-format'] = IppTag.NAME
ATTRIBUTE_TAG_MAP['print-color-mode'] = IppTag.KEYWORD

DICT_KEY_TO_TAG: dict[str, IppTag] = {
    "operation-attributes-tag": IppTag.OPERATION,
    "job-attributes-tag": IppTag.JOB,
    "printer-attributes-tag": IppTag.PRINTER
}


def default_tag_for_value(key: str, value: Any) -> IppTag:
    if key in ATTRIBUTE_TAG_MAP:
        return ATTRIBUTE_TAG_MAP[key]
    if key.endswith('-supported') or key.endswith('-default') or key.endswith('-configured') \
            or key.endswith('-supplied'):
        key2 = key[:key.rindex('-')]
        if key2 in ATTRIBUTE_TAG_MAP:
            return ATTRIBUTE_TAG_MAP[key2]
    if isinstance(value, bool):
        return IppTag.BOOLEAN
    if isinstance(value, int):
        return IppTag.INTEGER
    if isinstance(value, dict):
        return IppTag.BEGIN_COLLECTION
    raise NotImplementedError(f'Unknown tag for {key!r} / {value!r}')


def encode_value(value: Any, tag: IppTag) -> bytes:
    # including length field, if necessary
    if tag in (IppTag.INTEGER, IppTag.ENUM):
        if isinstance(value, bytes):
            assert len(value) == 4
            return struct.pack('>H', 4) + value
        return struct.pack(">hi", 4, value)
    elif tag == IppTag.BOOLEAN:
        return struct.pack(">h?", 1, value)
    elif tag == IppTag.BEGIN_COLLECTION:
        return encode_collection_inner(value)
    elif tag == IppTag.RESOLUTION:
        return struct.pack(">hiib", 9, *value)
    else:
        if isinstance(value, str):
            encoded_value = value.encode("utf-8")
        elif isinstance(value, bytes):
            encoded_value = value
        else:
            raise NotImplementedError(str(type(value)))
        return struct.pack(">h", len(encoded_value)) + encoded_value


def encode_collection_attribute(name: str, coll: dict) -> bytes:
    # 3.1.6 Collection Attribute
    binary_name = name.encode('utf-8')
    result = struct.pack('>BH', IppTag.BEGIN_COLLECTION.value, len(binary_name)) + binary_name
    result += encode_collection_inner(coll)
    return result


def encode_collection_inner(coll: dict) -> bytes:
    # including end tag, excluding begin tag
    result = b'\x00\x00'
    for key, value in coll.items():
        binary_key = key.encode('utf-8')
        result += struct.pack('>BHH', IppTag.MEMBER_NAME.value, 0, len(binary_key)) + binary_key
        tag = default_tag_for_value(key, value)
        result += struct.pack('>BH', tag, 0) + encode_value(value, tag)
    result += struct.pack('>BHH', IppTag.END_COLLECTION.value, 0, 0)
    return result


def encode_attribute(name: str, values: Any, tag: IppTag | None) -> bytes:
    if isinstance(values, list):
        result = encode_attribute(name, values[0], tag)
        for value in values[1:]:
            # 3.1.5 Additional-value
            result += encode_attribute('', value, tag or default_tag_for_value(name, value))
        return result

    # handle None tag
    if tag is None:
        tag = default_tag_for_value(name, values)
        if tag is None:
            raise Exception(f'NO TAG FOR {name}')

    if isinstance(values, dict):
        return encode_collection_attribute(name, values)

    # 3.1.4 Attribute-with-one-value
    binary_name = name.encode('utf-8')
    return struct.pack('>BH', tag.value, len(binary_name)) + binary_name + encode_value(values, tag)


def encode_attributes(attributes: dict[IppTag, list[tuple[str, Any, IppTag | None]]]) -> bytes:
    result = b''
    for begin_tag in sorted(attributes):  # 3.1.2 Attribute Group
        result += encode_attributes_section(begin_tag, attributes[begin_tag])
    return result


def encode_attributes_section(section: IppTag, attributes: list[tuple[str, Any, IppTag | None]]) -> bytes:
    result = struct.pack('>B', section.value)
    for name, values, tag in attributes:
        result += encode_attribute(name, values, tag)
    return result


@dataclass
class IppMessage:
    version_number: tuple[int, int] = (1, 1)
    status_code: int = IppStatus.OK.value
    request_id: int = 0

    operation_attributes: dict = field(default_factory=dict)
    jobs: list[dict] = field(default_factory=list)
    printers: list[dict] = field(default_factory=list)

    data: bytes = b''

    @property
    def operation_id(self) -> IppOperation:
        return IppOperation(self.status_code)  # same field

    def encode(self) -> bytes:
        op_attributes: list[tuple[str, Any, IppTag | None]] = []
        special_attrs = ('attributes-charset', 'attributes-natural-language')
        for special_attr in special_attrs:
            if special_attr in self.operation_attributes:
                op_attributes.append((special_attr, self.operation_attributes[special_attr], None))
        op_attributes += [(k, v, None) for k, v in self.operation_attributes.items() if k not in special_attrs]
        attributes = [
            (IppTag.OPERATION, op_attributes)
        ]
        for job in self.jobs:
            attributes.append((IppTag.JOB, [(k, v, None) for k, v in job.items()]))
        for printer in self.printers:
            attributes.append((IppTag.PRINTER, [(k, v, None) for k, v in printer.items()]))
        return struct.pack('>BBHI', *self.version_number, self.status_code, self.request_id) + \
            b''.join(encode_attributes_section(tag, attrs) for tag, attrs in attributes) + \
            struct.pack('>B', IppTag.END.value) + \
            self.data

    @classmethod
    def decode(cls, b: bytes) -> 'IppMessage':
        try:
            d = parser.parse(b, contains_data=True)
        except:
            print('CANNOT DECODE:', b)
            raise
        return IppMessage(
            version_number=d['version'],
            status_code=d['status-code'],
            request_id=d['request-id'],
            operation_attributes=d['operation-attributes'],
            jobs=d['jobs'],
            printers=d['printers'],
            data=d['data'],
        )
