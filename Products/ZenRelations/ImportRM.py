###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""ImportRM

Export RelationshipManager objects from a zope database

$Id: ImportRM.py,v 1.3 2003/10/03 16:16:01 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import sys
import os
import types
import urllib2
import transaction
from urlparse import urlparse
from xml.sax import make_parser, saxutils
from xml.sax.handler import ContentHandler

from Acquisition import aq_base
from zExceptions import NotFound

from DateTime import DateTime

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import importClass
from Products.ZenUtils.Utils import getObjByPath

from Products.ZenRelations.Exceptions import *

import logging
log = logging.getLogger('zen.ImportRM')

class ImportRM(ZCmdBase, ContentHandler):

    rootpath = ""
    skipobj = 0

    def __init__(self, noopts=0, app=None, keeproot=False):
        ZCmdBase.__init__(self, noopts, app, keeproot)
        ContentHandler.__init__(self)
        if hasattr(self.options, 'infile'): 
            self.infile = self.options.infile
        else: 
            self.infile = ""
        if hasattr(self.options, 'noCommit'): 
            self.noCommit = self.options.noCommit
        else:
            self.noCommit = True
        if hasattr(self.options, 'noindex'):
            self.noindex = self.options.noindex
        else:
            self.noindex = True

    def context(self):
        return self.objstack[-1]


    def cleanattrs(self, attrs):
        myattrs = {}
        for key, val in attrs.items():
            myattrs[key] = str(val)
        return myattrs

        
    def startElement(self, name, attrs):
        attrs = self.cleanattrs(attrs)
        if self.skipobj > 0: 
            self.skipobj += 1
            return
        log.debug("tag %s, context %s", name, self.context().id)
        if name == 'object':
            obj = self.createObject(attrs)
            if (not self.noindex  
                and hasattr(aq_base(obj), 'reIndex')
                and not self.rootpath):
                self.rootpath = obj.getPrimaryId()
            self.objstack.append(obj)
        elif name == 'tomanycont' or name == 'tomany':
            nextobj = self.context()._getOb(attrs['id'],None)
            if nextobj is None: 
                self.skipobj = 1 
                return
            else:
                self.objstack.append(nextobj)
        elif name == 'toone':
            relname = attrs.get('id')
            log.debug("toone %s, on object %s", relname, self.context().id)
            rel = getattr(aq_base(self.context()),relname, None)
            if rel is None: 
                print 'skip toone'
                return
            objid = attrs.get('objid')
            self.addLink(rel, objid)
        elif name == 'link':
            self.addLink(self.context(), attrs['objid'])
        elif name == 'property':
            self.curattrs = attrs


    def endElement(self, name):
        if self.skipobj > 0: 
            self.skipobj -= 1
            return
        if name in ('object', 'tomany', 'tomanycont'):
            obj = self.objstack.pop()
            if hasattr(aq_base(obj), 'index_object'):
                obj.index_object()
            if self.rootpath == obj.getPrimaryId():
                log.info("calling reIndex %s", obj.getPrimaryId())
                obj.reIndex()
                self.rootpath = ""
        elif name == 'objects':
            log.info("End loading objects")
            log.info("Processing links")
            self.processLinks()
            if not self.noCommit:
                self.commit()
            log.info("Loaded %d objects into database" % self.objectnumber)
        elif name == 'property':
            self.setProperty(self.context(), self.curattrs, self.charvalue)
            self.charvalue = ""
       

    def characters(self, chars):
        self.charvalue += saxutils.unescape(chars)


    def createObject(self, attrs):
        """create an object and set it into its container"""
        id = attrs.get('id')
        obj = None
        try:
            if id.startswith("/"):
                obj = getObjByPath(self.app, id)
            else:
                obj = self.context()._getOb(id)
        except (KeyError, AttributeError, NotFound): pass
        if obj is None:
            klass = importClass(attrs.get('module'), attrs.get('class'))
            if id.find("/") > -1:
                contextpath, id = os.path.split(id)
                self.objstack.append(
                    getObjByPath(self.context(), contextpath))
            obj = klass(id)
            self.context()._setObject(obj.id, obj)
            obj = self.context()._getOb(obj.id)
            self.objectnumber += 1
            if self.objectnumber % 5000 == 0: transaction.savepoint()
            log.debug("Added object %s to database" % obj.getPrimaryId())
        else:
            log.warn("Object %s already exists skipping" % id)
        return obj


    def setProperty(self, obj, attrs, value):
        """Set the value of a property on an object.
        """
        name = attrs.get('id')
        proptype = attrs.get('type')
        setter = attrs.get("setter",None)
        log.debug("setting object %s att %s type %s value %s" 
                            % (obj.id, name, proptype, value))
        value = value.strip()
        try: value = str(value)
        except UnicodeEncodeError: pass
        if proptype == 'selection':
            try:
                firstElement = getattr(obj, name)[0]
                if type(firstElement) in types.StringTypes:
                    proptype = 'string'
            except (TypeError, IndexError):
                proptype = 'string'
        if proptype == "date":
            try: value = float(value)
            except ValueError: pass
            value = DateTime(value)
        elif proptype != "string" and proptype != 'text':
            try: value = eval(value)
            except SyntaxError: pass
        if not obj.hasProperty(name):
            obj._setProperty(name, value, type=proptype, setter=setter)
        else:
            obj._updateProperty(name, value)


    def addLink(self, rel, objid):
        """build list of links to form after all objects have been created
        make sure that we don't add other side of a bidirectional relation"""
        self.links.append((rel.getPrimaryId(), objid))


    def processLinks(self):
        """walk through all the links that we saved and link them up"""
        for relid, objid in self.links:
            try:
                log.debug("Linking relation %s to object %s",
                                relid,objid)
                rel = getObjByPath(self.app, relid)
                obj = getObjByPath(self.app, objid)
                if not rel.hasobject(obj):
                    rel.addRelation(obj)
            except:
                log.critical(
                    "Failed linking relation %s to object %s",relid,objid)
                #raise
                                


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)

        self.parser.add_option('-i', '--infile',
                    dest="infile",
                    help="input file for import default is stdin")
        
        self.parser.add_option('-x', '--commitCount',
                    dest='commitCount',
                    default=20,
                    type="int",
                    help='how many lines should be loaded before commit')

        self.parser.add_option('--noindex',
                    dest='noindex',action="store_true",default=False,
                    help='Do not try to index data that was just loaded')

        self.parser.add_option('-n', '--noCommit',
                    dest='noCommit',
                    action="store_true",
                    default=0,
                    help='Do not store changes to the Dmd (for debugging)')

    def loadObjectFromXML(self, xmlfile=''):
        """This method can be used to load data for the root of Zenoss (default
        behavior) or it can be used to operate on a specific point in the
        Zenoss hierarchy (ZODB).

        Upon loading the XML file to be processed, the content of the XML file
        is handled (processed) by the methods in this class.
        """
        self.objstack = [self.app]
        self.links = []
        self.objectnumber = 0
        self.charvalue = ""
        if xmlfile and type(xmlfile) in types.StringTypes:
            self.infile = open(xmlfile)
        elif hasattr(xmlfile, 'read'):
            self.infile = xmlfile
        elif self.infile:
            self.infile = open(self.infile)
        else:
            self.infile = sys.stdin
        parser = make_parser()
        parser.setContentHandler(self)
        parser.parse(self.infile)
        self.infile.close()

    def loadDatabase(self):
        """The default behavior of loadObjectFromXML() will be to use the Zope
        app object, and thus operatate on the whole of Zenoss.
        """
        self.loadObjectFromXML()

    def commit(self):
        trans = transaction.get()
        trans.note('Import from file %s using %s' 
                    % (self.infile, self.__class__.__name__))
        trans.commit()


class NoLoginImportRM(ImportRM):
    """An ImportRM that does not call the __init__ method on ZCmdBase"""
    def __init__(self, app):
        self.app = app
        ContentHandler.__init__(self)
        self.infile = ""
        self.noCommit = True
        self.noindex = True

if __name__ == '__main__':
    im = ImportRM()
    im.loadDatabase()
