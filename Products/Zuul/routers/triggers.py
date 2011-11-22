###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from operator import itemgetter
from Products import Zuul
from zope.component import getUtilitiesFor
from Products.ZenModel.interfaces import IAction
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse
from Products.Zuul.decorators import serviceConnectionError
from zenoss.protocols.protobufs.zep_pb2 import RULE_TYPE_JYTHON
from Products.ZenMessaging.audit import audit

import logging

log = logging.getLogger('zen.triggers');

class TriggersRouter(DirectRouter):
    """
    Router for Triggers UI section under Events.
    """

    def _getFacade(self):
        return Zuul.getFacade('triggers', self)

    @serviceConnectionError
    def getTriggers(self, **kwargs):
        return DirectResponse.succeed(data=self._getFacade().getTriggers())

    @serviceConnectionError
    def getTriggerList(self, **unused):
        return DirectResponse.succeed(data=self._getFacade().getTriggerList())

    @serviceConnectionError
    def addTrigger(self, newId):
        data = self._getFacade().addTrigger(newId)
        audit('UI.Trigger.Add', newId)
        return DirectResponse.succeed(data=data)

    @serviceConnectionError
    def removeTrigger(self, uuid):
        updated_count = self._getFacade().removeTrigger(uuid)
        audit('UI.Trigger.Remove', uuid)
        msg = "Trigger removed successfully. {count} {noun} {verb} updated.".format(
            count = updated_count,
            noun = 'notification' if updated_count == 1 else 'notifications',
            verb = 'was' if updated_count == 1 else 'were'
        )
        return DirectResponse.succeed(msg=msg, data=None)

    @serviceConnectionError
    def getTrigger(self, uuid):
        return DirectResponse.succeed(data=self._getFacade().getTrigger(uuid))

    @serviceConnectionError
    def updateTrigger(self, **data):
        data['rule']['api_version'] = 1
        data['rule']['type'] = RULE_TYPE_JYTHON
        triggerUid = data['uuid']
        response = self._getFacade().updateTrigger(**data)
        audit('UI.Trigger.Edit', triggerUid, data_=data)
        return DirectResponse.succeed(msg="Trigger updated successfully.", data=response)

    @serviceConnectionError
    def parseFilter(self, source):
        try:
            response = self._getFacade().parseFilter(source)
            return DirectResponse.succeed(data=response)
        except Exception, e:
            log.exception(e)
            return DirectResponse.exception(e,
                'Error parsing filter source. Please check your syntax.')


    # notification subscriptions
    @serviceConnectionError
    def getNotifications(self, sort=None, dir=None, page=None, start=None, limit=None):
        response = self._getFacade().getNotifications()
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def addNotification(self, newId, action):
        response = self._getFacade().addNotification(newId, action)
        audit('UI.Notification.Add', newId)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def removeNotification(self, uid):
        response = self._getFacade().removeNotification(uid)
        audit('UI.Notification.Remove', uid)
        return DirectResponse.succeed(msg="Notification removed successfully.", data=response)

    @serviceConnectionError
    def getNotificationTypes(self, query=''):
        utils = getUtilitiesFor(IAction)
        actionTypes = sorted((dict(id=id, name=util.name) for id, util in utils), key=itemgetter('id'))
        log.debug('notification action types are: %s' % actionTypes)
        return DirectResponse.succeed(data=actionTypes)

    @serviceConnectionError
    def getNotification(self, uid):
        response = self._getFacade().getNotification(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def updateNotification(self, **data):
        notificationUid = data['uid']
        response = self._getFacade().updateNotification(**data)
        audit('UI.Notification.Edit', notificationUid, data_=data)
        return DirectResponse.succeed(msg="Notification updated successfully.", data=Zuul.marshal(response))

    @serviceConnectionError
    def getRecipientOptions(self, **kwargs):
        data = self._getFacade().getRecipientOptions()
        return DirectResponse.succeed(data=data);

    # subscription windows
    @serviceConnectionError
    def getWindows(self, uid, **kwargs):
        response = self._getFacade().getWindows(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def addWindow(self, contextUid, newId):
        response = self._getFacade().addWindow(contextUid, newId)
        audit('UI.NotificationWindow.Add', newId, notification=contextUid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def removeWindow(self, uid):
        response = self._getFacade().removeWindow(uid)
        audit('UI.NotificationWindow.Remove', uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def getWindow(self, uid):
        response = self._getFacade().getWindow(uid)
        return DirectResponse.succeed(data=Zuul.marshal(response))

    @serviceConnectionError
    def updateWindow(self, **data):
        windowUid = data['uid']
        response = self._getFacade().updateWindow(data)
        audit('UI.NotificationWindow.Edit', windowUid, data_=data)
        return DirectResponse.succeed(data=Zuul.marshal(response))
