
#
# soaplib - Copyright (C) Soaplib contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

import soaplib
from lxml import etree
from soaplib.serializers import Base

_ns_xsi = soaplib.ns_xsi

class _Soap11Fault(Exception, Base):
    __type_name__ = "Fault"

    def __init__(self, faultcode='Server', faultstring="", detail=""):
        self.faultcode = faultcode
        self.faultstring = faultstring
        self.detail = detail

    @classmethod
    def to_xml(cls, value, tns, parent_elt, name=None):
        if name is None:
            name = cls.get_type_name()
        element = etree.SubElement(parent_elt, "{%s}%s" % (tns,name))

        etree.SubElement(element, '{%s}faultcode' % tns).text = value.faultcode
        etree.SubElement(element, '{%s}faultstring' % tns).text = value.faultstring
        etree.SubElement(element, '{%s}detail' % tns).text = value.detail

    @classmethod
    def from_xml(cls, element):
        code = element.find('faultcode').text
        string = element.find('faultstring').text
        detail_element = element.find('detail')
        if detail_element is not None:
            if len(detail_element.getchildren()):
                detail = etree.tostring(detail_element)
            else:
                detail = element.find('detail').text
        else:
            detail = ''
        return Fault(faultcode=code, faultstring=string, detail=detail)

    @classmethod
    def add_to_schema(cls, schema_dict):
        complex_type = etree.Element('complexType')
        complex_type.set('name', cls.get_type_name())
        sequenceNode = etree.SubElement(complex_type, 'sequence')

        element = etree.SubElement(sequenceNode, 'element')
        element.set('name', 'detail')
        element.set('{%s}type' % _ns_xsi, 'xs:string')

        element = etree.SubElement(sequenceNode, 'element')
        element.set('name', 'message')
        element.set('{%s}type' % _ns_xsi, 'xs:string')

        schema_dict.add_complex_type(cls, complex_type)

        top_level_element = etree.Element('element')
        top_level_element.set('name', 'ExceptionFaultType')
        top_level_element.set('{%s}type' % _ns_xsi, cls.get_type_name_ns())

        schema_dict.add_element(cls, top_level_element)

class _Soap12Fault(Exception, Base):
    # TODO:
    # * add_to_schema
    # * Reason not in English
    # * Detail not of text type
    # * Customized Node and Role

    __type_name__ = "Fault"

    def __init__(self, faultcode='Server', faultstring="", detail=""):
        if faultcode and isinstance(faultcode, (list, tuple)):
            self.faultcode = faultcode[0]
            self.faultsubcodes = faultcode[1:]
        else:
            self.faultcode = faultcode or ""
            self.faultsubcodes = []
        self.faultstring = faultstring
        self.detail = detail

    @classmethod
    def __to_prefix(cls, text, parent_nsmap, element_nsmap):
        if not (text.startswith('{') and text.find('}') >= 0):
            return text

        namespace, code = text.split('}', 1)
        namespace = namespace[1:]

        def find_prefix(nsmap):
            for pr, ns in nsmap.items():
                if namespace == ns:
                    return pr
            else:
                return None

        prefix = find_prefix(parent_nsmap) or find_prefix(element_nsmap)
        if prefix:
            return "%s:%s" % (prefix, code)
        else:
            i = 0
            while ("s%i" % i in parent_nsmap or "s%i" % i in element_nsmap):
                i += 1
            element_nsmap["s%i" % i] = namespace
            return "s%i:%s" % (i, code)

    @classmethod
    def __to_namespace(cls, text, nsmap):
        if text.find(':') >= 0:
            prefix, code = text.split(":", 1)
            if prefix in nsmap:
                return "{%s}%s" % (nsmap[prefix], code)
        return text

    @classmethod
    def to_xml(cls, value, tns, parent_elt, name=None):
        ns_env = soaplib.ns_soap12_env
        ns_xml = soaplib.ns_xml
        element_nsmap = {}

        if name is None:
            name = cls.get_type_name()

        codeEl = _codeEl = etree.Element("{%s}Code" % ns_env)
        etree.SubElement(_codeEl, "{%s}Value" % ns_env).text = \
                cls.__to_prefix(value.faultcode, parent_elt.nsmap, element_nsmap)
        for code in value.faultsubcodes:
            subcodeEl = etree.SubElement(_codeEl, "{%s}Subcode" % ns_env)
            etree.SubElement(subcodeEl, "{%s}Value" % ns_env).text = \
                    cls.__to_prefix(code, parent_elt.nsmap, element_nsmap)
            _codeEl = subcodeEl

        element = etree.SubElement(parent_elt, "{%s}%s" % (tns,name), nsmap=element_nsmap)
        element.append(codeEl)

        reasonEl = etree.SubElement(element, "{%s}Reason" % ns_env)
        reasontextEl = etree.SubElement(reasonEl, "{%s}Text" % ns_env)
        reasontextEl.set("{%s}lang" % ns_xml, "en")
        reasontextEl.text = value.faultstring

        etree.SubElement(element, "{%s}Node" % ns_env).text = "http://www.w3.org/2003/05/soap-envelope/node/ultimateReceiver"
        etree.SubElement(element, "{%s}Role" % ns_env).text = "http://www.w3.org/2003/05/soap-envelope/role/ultimateReceiver"

        detailEl = etree.SubElement(element, "{%s}Detail" % ns_env)
        etree.SubElement(detailEl, "{%s}Text" % ns_env).text = value.detail

    @classmethod
    def from_xml(cls, element):
        ns_env = soaplib.ns_soap12_env

        faultcode = []
        codeEl = element.find("{%s}Code" % ns_env)
        while not codeEl is None:
            valueEl = codeEl.find("{%s}Value" % ns_env)
            if not valueEl is None:
                faultcode.append(cls.__to_namespace(valueEl.text or "", element.nsmap))
            codeEl = codeEl.find("{%s}Subcode" % ns_env)

        faultstring = ""
        reasonEl = element.find("{%s}Reason" % ns_env)
        if not reasonEl is None:
            reasontextEl = reasonEl.find("{%s}Text" % ns_env)
            if not reasontextEl is None:
                faultstring = reasontextEl.text or ""

        detail = ""
        detailEl = element.find("{%s}Detail" % ns_env)
        if not detailEl is None:
            detailtextEl = detailEl.find("{%s}Text" % ns_env)
            if not detailtextEl is None:
                detail = detailtextEl.text or ""
        
        return cls(faultcode, faultstring, detail)

    @classmethod
    def add_to_schema(cls, schema_dict):
        raise Exception("not yet implemented")

Fault = _Soap12Fault
