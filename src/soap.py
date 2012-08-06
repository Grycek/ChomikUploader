from itertools import groupby
from xml.dom.minidom import Document
import xml.parsers.expat
import copy


class SOAP(object):
    def __init__(self):
        pass
    
    def soap_xml_to_dict(self, xml):
        return parse(xml)
    
    def soap_dict_to_xml(self, soap_dict, method):
        '''
        method = i.e Auth
        '''
        xml  = dict2xml(soap_dict)
        text = xml.replace("<ROOT>", "")
        text = text.replace("</ROOT>", "")
        prefix = """<?xml version="1.0" encoding="UTF-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>"""
        prefix += "<" + method + ' xmlns="http://chomikuj.pl/"' + '>'
        suffix = "</" + method + ">"
        suffix += """</s:Body></s:Envelope>"""
        return prefix + text + suffix
    







###################################################################    

def dict2xml(xml_list):
    if type(xml_list) == list:
        return "".join([dict2xml(i) for i in xml_list])
    elif type(xml_list) == tuple:
        return "<" + xml_list[0] + ">" + dict2xml(xml_list[1])  + "</" + xml_list[0] + ">"
    else:
        return str(xml_list)


##################################################################

__author__ = 'Martin Blech'
__version__ = '0.1.dev'
__license__ = 'MIT'

class ParsingInterrupted(Exception): pass

class DictSAXHandler:
    def __init__(self,
            item_depth=0,
            xml_attribs=True,
            item_callback=lambda *args: True,
            attr_prefix='@',
            cdata_key='#text',
            force_cdata=False):
        self.path = []
        self.stack = []
        self.data = None
        self.item = None
        self.item_depth = item_depth
        self.xml_attribs = xml_attribs
        self.item_callback = item_callback
        self.attr_prefix = attr_prefix;
        self.cdata_key = cdata_key
        self.force_cdata = force_cdata

    def startElement(self, name, attrs):
        self.path.append((name, attrs or None))
        if len(self.path) > self.item_depth:
            self.stack.append((self.item, self.data))
            attrs = dict((self.attr_prefix+key, value)
                    for (key, value) in attrs.items())
            self.item = self.xml_attribs and attrs or None
            self.data = None
    
    def endElement(self, name):
        if len(self.path) == self.item_depth:
            item = self.item
            if item is None:
                item = self.data
            should_continue = self.item_callback(self.path, item)
            if not should_continue:
                raise ParsingInterrupted()
        if len(self.stack):
            item, data = self.item, self.data
            self.item, self.data = self.stack.pop()
            if self.force_cdata and item is None:
                item = {}
            if item is not None:
                if data:
                    item[self.cdata_key] = data
                self.push_data(name, item)
            else:
                self.push_data(name, data)
        else:
            self.item = self.data = None
        self.path.pop()

    def characters(self, data):
        if data.strip():
            if not self.data:
                self.data = data
            else:
                self.data += data

    def push_data(self, key, data):
        if self.item is None:
            self.item = {}
        try:
            value = self.item[key]
            if isinstance(value, list):
                value.append(data)
            else:
                self.item[key] = [value, data]
        except KeyError:
            self.item[key] = data

def parse(xml_input, *args, **kwargs):
    """Parse the given XML input and convert it into a dictionary.

    `xml_input` can either be a `string` or a file-like object.

    If `xml_attribs` is `True`, element attributes are put in the dictionary
    among regular child elements, using `@` as a prefix to avoid collisions. If
    set to `False`, they are just ignored.

    Simple example::

        >>> doc = xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>
        ... \"\"\")
        >>> doc['a']['@prop']
        u'x'
        >>> doc['a']['b']
        [u'1', u'2']

    If `item_depth` is `0`, the function returns a dictionary for the root
    element (default behavior). Otherwise, it calls `item_callback` every time
    an item at the specified depth is found and returns `None` in the end
    (streaming mode).

    The callback function receives two parameters: the `path` from the document
    root to the item (name-attribs pairs), and the `item` (dict). If the
    callback's return value is false-ish, parsing will be stopped with the
    :class:`ParsingInterrupted` exception.

    Streaming example::

        >>> def handle(path, item):
        ...     print 'path:%s item:%s' % (path, item)
        ...     return True
        ... 
        >>> xmltodict.parse(\"\"\"
        ... <a prop="x">
        ...   <b>1</b>
        ...   <b>2</b>
        ... </a>\"\"\", item_depth=2, item_callback=handle)
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:1
        path:[(u'a', {u'prop': u'x'}), (u'b', None)] item:2

    """
    handler = DictSAXHandler(*args, **kwargs)
    parser = xml.parsers.expat.ParserCreate()
    parser.StartElementHandler = handler.startElement
    parser.EndElementHandler = handler.endElement
    parser.CharacterDataHandler = handler.characters
    if hasattr(xml_input, 'read'):
        parser.ParseFile(xml_input)
    else:
        parser.Parse(xml_input, True)
    return handler.item

if __name__ == '__main__':
    s = SOAP()
    print parse("""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><AuthResponse xmlns="http://chomikuj.pl/"><AuthResult xmlns:a="http://chomikuj.pl" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"><a:status>Ok</a:status><a:errorMessage i:nil="true"/><a:hamsterId>5762328</a:hamsterId><a:publisherId i:nil="true"/><a:name>tmp_chomik1</a:name><a:token>092fb999-6494-48b5-b6fd-859c1595f7ab</a:token></AuthResult></AuthResponse></s:Body></s:Envelope>""")
    print parse("""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><AuthResponse xmlns="http://chomikuj.pl/"><AuthResult xmlns:a="http://chomikuj.pl" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"><a:status>Ok</a:status><a:errorMessage i:nil="true"/><a:hamsterId>5762328</a:hamsterId><a:publisherId i:nil="true"/><a:name>tmp_chomik1</a:name><a:token>092fb999-6494-48b5-b6fd-859c1595f7ab</a:token></AuthResult></AuthResponse></s:Body></s:Envelope>""")    
    print s.soap_xml_to_dict("""<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><AuthResponse xmlns="http://chomikuj.pl/"><AuthResult xmlns:a="http://chomikuj.pl" xmlns:i="http://www.w3.org/2001/XMLSchema-instance"><a:status>Ok</a:status><a:errorMessage i:nil="true"/><a:hamsterId>5762328</a:hamsterId><a:publisherId i:nil="true"/><a:name>tmp_chomik1</a:name><a:token>092fb999-6494-48b5-b6fd-859c1595f7ab</a:token></AuthResult></AuthResponse></s:Body></s:Envelope>""")
    Y = {'Body': {'client': [{'version': '2.0.4.3<', 'name': 'chomikbox'} ], 'ver': '4', 'name': 'tmp_chomik1', 'passHash': 'ba2e57cbd8546cffd7db6bfd4077758b'}}
    X = """<T uri="boo"><a n="1"/><a n="2"/><b n="3"><c x="y"/></b></T>"""
    user = "a"
    password = "b"
    example = {'ROOT':{'client':{'version':'2.0.4.3','name':'chomikbox' }, 'ver' : '4', 'name' : user, 'passHash': password}}
    example = [('ROOT',[('name' , user), ('passHash', password), ('ver' , '4'), ('client',[('name','chomikbox'),('version','2.0.4.3') ]) ])]
    #example = [('ROOT', [('client', 'w')])]
    #example = {'ROOT':{'client':{'version':'2.0.4.3','name':'chomikbox' }, 'ver' : '4', 'name' : 'tmp_chomik1', 'passHash': 'ba2e57cbd8546cffd7db6bfd4077758b'}}
    print dict2xml(example)
    print dict2xml(example)
    
    print s.soap_dict_to_xml(example, "Auth")
