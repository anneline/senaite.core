# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from bika.lims import senaiteMessageFactory as _
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.behavior.interfaces import IBehaviorAssignable
from plone.behavior.registration import BehaviorRegistration
from plone.dexterity.behavior import DexterityBehaviorAssignable
from plone.dexterity.schema import SCHEMA_CACHE
from plone.supermodel import model
from plone.supermodel.directives import fieldset
from Products.CMFCore import permissions
from senaite.core.api import label as label_api
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.interfaces import ICanHaveLabels
from senaite.core.z3cform.widgets.queryselect import QuerySelectWidgetFactory
from zope import schema
from zope.component import adapter
from zope.interface import implementer
from zope.interface import provider


@implementer(IBehaviorAssignable)
@adapter(ICanHaveLabels)
class LabelBehaviorAssignable(DexterityBehaviorAssignable):
    """Extend label behavior if the context provides the interface `ICanHaveLabels`
    """
    def __init__(self, context):
        self.context = context

    def supports(self, behavior_interface):
        for behavior in self.enumerateBehaviors():
            if behavior_interface in behavior.interface._implied:
                return True
        return False

    def enumerateBehaviors(self):
        portal_type = self.context.portal_type
        behaviors = SCHEMA_CACHE.behavior_registrations(portal_type)
        registered = False
        for behavior in behaviors:
            if behavior.marker == ICanHaveLabels:
                registered = True
            yield behavior
        # additionally yield the schema registration if it was not already
        # registered via the FTI
        if not registered:
            yield self.label_registration

    @property
    def label_registration(self):
        return BehaviorRegistration(
            title="Label schema extender",
            description="Adds the ability to add/remove labels",
            interface=ILabelSchema,
            marker=ICanHaveLabels,
            factory=LabelSchema,
        )


@provider(IFormFieldProvider)
class ILabelSchema(model.Schema):
    """Behavior with schema fields to allow to add/remove labels
    """
    fieldset(
        "labels",
        label=u"Labels",
        fields=["Labels"])

    directives.widget(
        "Labels",
        QuerySelectWidgetFactory,
        catalog=SETUP_CATALOG,
        search_index="Title",
        value_key="title",
        search_wildcard=True,
        multi_valued=True,
        allow_user_value=True,
        hide_input_after_select=False,
        query={
            "portal_type": "Label",
            "is_active": True,
            "sort_on": "title",
        },
        columns=[
            {
                "name": "title",
                "width": "100",
                "align": "left",
                "label": _(u"Label"),
            },
        ],
        display_template="<a href='${url}'>${title}</a>",
        limit=5,
    )
    Labels = schema.List(
        title=_(u"label_Labels", default=u"Labels"),
        description=_(u"description_Labels", default=u"Attached labels"),
        value_type=schema.TextLine(title=u"Label"),
        required=False,
    )


@implementer(ILabelSchema)
@adapter(ICanHaveLabels)
class LabelSchema(object):
    """Factory that provides the extended label fields
    """
    security = ClassSecurityInfo()

    def __init__(self, context):
        self.context = context

    @security.protected(permissions.View)
    def getLabels(self):
        return label_api.get_obj_labels(self.context)

    @security.protected(permissions.ModifyPortalContent)
    def setLabels(self, value):
        labels = label_api.to_labels(value)
        return label_api.set_obj_labels(self.context, labels)

    Labels = property(getLabels, setLabels)
