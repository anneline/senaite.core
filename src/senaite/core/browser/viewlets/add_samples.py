# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE.
#
# SENAITE.CORE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2018-2023 by it's authors.
# Some rights reserved, see README and LICENSE.

from bika.lims import api
from bika.lims.interfaces import IBatch
from bika.lims.permissions import AddAnalysisRequest
from plone.app.layout.viewlets import ViewletBase
from plone.memoize.instance import memoize
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.core.interfaces import ISamplesView
from zope.component import getMultiAdapter


class AddSamplesViewlet(ViewletBase):
    index = ViewPageTemplateFile("templates/add_samples.pt")

    def available(self):
        """Check if the add samples viewlet should be rendered
        """
        if not ISamplesView.providedBy(self.view):
            return False
        container = self.get_samples_container()
        if not api.security.check_permission(AddAnalysisRequest, container):
            return False
        return True

    def get_sample_add_number(self):
        """Return the default number of Samples to add
        """
        setup = api.get_setup()
        return setup.getDefaultNumberOfARsToAdd() or 1

    def get_add_url(self):
        """Return the sample add URL
        """
        container = self.get_samples_container()
        return "{}/ar_add".format(api.get_url(container))

    def get_samples_container(self):
        """Returns the container object where new samples will be added
        """
        if IBatch.providedBy(self.context):
            return self.context
        return api.get_current_client() or self.context

    @property
    @memoize
    def theme_view(self):
        return getMultiAdapter(
            (self.context, self.request),
            name="senaite_theme")
