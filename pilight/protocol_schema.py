import json
import logging
import voluptuous as vol

from os import path


KEY_PROTOCOLS = "protocols"
KEY_DEVICES = "devices"
KEY_NAME = "name"
KEY_DATA_TYPE = "vartype"
KEY_OPTIONS = "options"
KEY_PROTOCOL = "protocol"


logger = logging.getLogger(__name__)


_types = {"string" : str,
          "number": vol.Any(int, float)}


def _default_schema():
    """Load the fefault schema.

    This is necessary until we have proper runtime protocol reporting support
    in the pilight daemon.
    """
    with open(path.join(path.dirname(__file__), "protocol_list.json")) as fp:
        return json.load(fp)


def _convert_datatype(type_data):
    if isinstance(type_data, (list, tuple)):
        if len(type_data) == 1:
            return _convert_datatype(type_data[0])
        return vol.Any([_convert_datatype(t) for t in type_data])
    
    return _types.get(type_data)


def _make_vol_schema(protocol_name, option_data):
    option_schema = {vol.Required(KEY_PROTOCOL): protocol_name}
    for option in option_data:
        option_schema[vol.Optional(option.get(KEY_NAME))] =\
                _convert_datatype(option.get(KEY_DATA_TYPE))

    return vol.Schema(option_schema)


class ProtocolSchema(object):
    def __init__(self, schema_data):
        self.name = schema_data.get(KEY_NAME)
        self.devices = schema_data.get(KEY_DEVICES)
        self.schema = _make_vol_schema(self.name, schema_data.get(KEY_OPTIONS))

    def validate(self, data):
        return self.schema(data)

    def __repr__(self):
        return "ProtocolSchema(name={}, schema={})".format(self.name,
                                                           self.schema)


class ProtocolRegistry(object):
    def __init__(self, schema=None):
        if schema is None:
            logger.info("Use default protocol data")
            schema = _default_schema()

        self._protocols = {}

        for protocol in schema.get("protocols"):
            protocol_schema = ProtocolSchema(protocol)
            self._protocols[protocol_schema.name] = protocol_schema
            logger.debug("Added protocol '{}'".format(protocol_schema.name))

    def validate(self, data, protocol_as_list=True):
        protocol = data.get(KEY_PROTOCOL)

        if protocol is None:
            raise RuntimeError("No protocol specified in data!")

        if isinstance(protocol, list):
            protocol = protocol[0]

        if protocol not in self._protocols:
            raise RuntimeError("Unknown protocol '{}'".format(protocol))

        protocol_schema = self._protocols[protocol]
        validated = protocol_schema.schema(data)

        if protocol_as_list:
            validated[KEY_PROTOCOL] = [protocol]

        return validated


