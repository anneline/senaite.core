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
# Copyright 2018-2021 by it's authors.
# Some rights reserved, see README and LICENSE.

import collections

from bika.lims import api
from bika.lims import bikaMessageFactory as _BMF
from bika.lims import senaiteMessageFactory as _
from bika.lims.utils import get_link
from bika.lims.utils import to_utf8
from Products.CMFPlone.utils import safe_unicode
from senaite.app.listing import ListingView
from senaite.core.catalog import REPORT_CATALOG
from senaite.core.permissions.sample import can_publish
from ZODB.POSException import POSKeyError


class ReportsListingView(ListingView):
    """Listing view of all generated reports
    """

    def __init__(self, context, request):
        super(ReportsListingView, self).__init__(context, request)

        self.catalog = REPORT_CATALOG
        self.contentFilter = {
            "portal_type": "ARReport",
            "path": {
                "query": api.get_path(self.context),
                "depth": 2,
            },
            "sort_on": "created",
            "sort_order": "descending",
        }

        self.form_id = "reports_listing"
        self.title = _("Analysis Reports")

        self.icon = "{}/{}".format(
            self.portal_url,
            "++resource++bika.lims.images/report_big.png"
        )
        self.context_actions = {}

        self.allow_edit = False
        self.show_select_column = True
        self.show_workflow_action_buttons = True
        self.pagesize = 30

        self.columns = collections.OrderedDict((
            ("Info", {
                "title": "",
                "toggle": True},),
            ("AnalysisRequest", {
                "title": _("Primary Sample"),
                "index": "sortable_title"},),
            ("Batch", {
                "title": _("Batch")},),
            ("State", {
                "title": _("Review State")},),
            ("PDF", {
                "title": _("Download PDF")},),
            ("FileSize", {
                "title": _("Filesize")},),
            ("Date", {
                "title": _("Published Date")},),
            ("PublishedBy", {
                "title": _("Published By")},),
            ("Sent", {
                "title": _("Email sent")},),
            ("Recipients", {
                "title": _("Recipients")},),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": "All",
                "contentFilter": {},
                "columns": self.columns.keys(),
                "custom_transitions": [],
            },
        ]

    def before_render(self):
        """Before render hook
        """
        self.init_custom_transitions()

    def init_custom_transitions(self):
        """Add custom transitions
        """
        custom_transitions = [
            self.custom_transition_download,
        ]
        if can_publish(self.context):
            custom_transitions.append(self.custom_transition_email)
            custom_transitions.append(self.custom_transition_publish)
        # hook in custom transitions
        for state in self.review_states:
            state["custom_transitions"].extend(custom_transitions)

    @property
    def custom_transition_email(self):
        """Custom transition to send reports via email
        """
        help_email_text = _(
            "Open email form to send the selected reports to the recipients. "
            "This will also publish the contained samples of the reports "
            "after the email was successfully sent.")

        return {
            "id": "send_email",
            "title": _("Email"),
            "url": "email",
            "css_class": "btn btn-outline-secondary",
            "help": help_email_text,
        }

    @property
    def custom_transition_download(self):
        """Custom transition to download reports
        """
        help_download_reports_text = _(
            "Download selected reports")

        return {
            "id": "download_reports",
            "title": _("Download"),
            # see senaite.core.browser.workflow
            "url": "workflow_action?action=download_reports",
            "css_class": "btn-outline-secondary",
            "help": help_download_reports_text,
        }

    @property
    def custom_transition_publish(self):
        """Custom transition to publish reports w/o sending email
        """
        help_publish_text = _(
            "Manually publish all contained samples of the selected reports.")

        return {
            "id": "publish_samples",
            "title": _("Publish"),
            # see senaite.core.browser.workflow
            "url": "workflow_action?action=publish_samples",
            "css_class": "btn-outline-success",
            "help": help_publish_text,
        }

    def get_filesize(self, pdf):
        """Compute the filesize of the PDF
        """
        try:
            filesize = float(pdf.get_size())
            return filesize / 1024
        except (POSKeyError, TypeError):
            return 0

    def localize_date(self, date):
        """Return the localized date
        """
        return self.ulocalized_time(date, long_format=1)

    def get_pdf(self, obj):
        """Get the report PDF
        """
        try:
            return obj.getPdf()
        except (POSKeyError, TypeError):
            return None

    def folderitem(self, obj, item, index):
        """Augment folder listing item
        """

        obj = api.get_object(obj)
        ar = obj.getAnalysisRequest()
        uid = api.get_uid(obj)
        review_state = api.get_workflow_status_of(ar)
        status_title = review_state.capitalize().replace("_", " ")

        # Report Info Popup
        # see: bika.lims.site.coffee for the attached event handler
        item["Info"] = get_link(
            "analysisreport_info?report_uid={}".format(uid),
            value="<i class='fas fa-info-circle'></i>",
            css_class="overlay_panel")

        item["replace"]["AnalysisRequest"] = get_link(
            ar.absolute_url(), value=ar.Title()
        )

        # Include Batch information of the primary Sample
        batch_id = ar.getBatchID()
        item["Batch"] = batch_id
        if batch_id:
            batch = ar.getBatch()
            item["replace"]["Batch"] = get_link(
                batch.absolute_url(), value=batch.Title()
            )

        pdf = self.get_pdf(obj)
        filesize = self.get_filesize(pdf)
        if filesize > 0:
            url = "{}/download_pdf".format(obj.absolute_url())
            item["replace"]["PDF"] = get_link(
                url, value="PDF", target="_blank")

        item["State"] = _BMF(status_title)
        item["state_class"] = "state-{}".format(review_state)
        item["FileSize"] = "{:.2f} Kb".format(filesize)
        fmt_date = self.localize_date(obj.created())
        item["Date"] = fmt_date
        item["PublishedBy"] = self.user_fullname(obj.Creator())

        item["Sent"] = _("No")
        if obj.getSendLog():
            item["Sent"] = _("Yes")

        # N.B. There is a bug in the current publication machinery, so that
        # only the primary contact get stored in the Attachment as recipient.
        #
        # However, we're interested to show here the full list of recipients,
        # so we use the recipients of the containing AR instead.
        recipients = []

        for recipient in self.get_recipients(ar):
            email = safe_unicode(recipient["EmailAddress"])
            fullname = safe_unicode(recipient["Fullname"])
            if email:
                value = u"<a href='mailto:{}'>{}</a>".format(email, fullname)
                recipients.append(value)
            else:
                message = _("No email address set for this contact")
                value = u"<span title='{}' class='text text-danger'>" \
                        u"⚠ {}</span>".format(message, fullname)
                recipients.append(value)

        item["replace"]["Recipients"] = ", ".join(recipients)

        # No recipient with email set preference found in the AR, so we also
        # flush the Recipients data from the Attachment
        if not recipients:
            item["Recipients"] = ""

        return item

    def get_recipients(self, ar):
        """Return the AR recipients in the same format like the AR Report
        expects in the records field `Recipients`
        """
        plone_utils = api.get_tool("plone_utils")

        def is_email(email):
            if not plone_utils.validateSingleEmailAddress(email):
                return False
            return True

        def recipient_from_contact(contact):
            if not contact:
                return None
            email = contact.getEmailAddress()
            return {
                "UID": api.get_uid(contact),
                "Username": contact.getUsername(),
                "Fullname": to_utf8(contact.Title()),
                "EmailAddress": email,
            }

        def recipient_from_email(email):
            if not is_email(email):
                return None
            return {
                "UID": "",
                "Username": "",
                "Fullname": email,
                "EmailAddress": email,
            }

        # Primary Contacts
        to = filter(None, [recipient_from_contact(ar.getContact())])
        # CC Contacts
        cc = filter(None, map(recipient_from_contact, ar.getCCContact()))
        # CC Emails
        cc_emails = ar.getCCEmails(as_list=True)
        cc_emails = filter(None, map(recipient_from_email, cc_emails))

        return to + cc + cc_emails
