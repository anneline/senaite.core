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

""" FOSS FIAStar
"""
from bika.lims.browser import BrowserView
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from plone.i18n.normalizer.interfaces import IIDNormalizer
from senaite.core.p3compat import cmp
from zope.component import getUtility
from bika.lims import bikaMessageFactory as _
from bika.lims.utils import t
from . import FOSSFIAStarCSVParser, FOSSFIAStarImporter
from six import StringIO
import json
import traceback
import csv

title = "FOSS - FIAStar"

class Export(BrowserView):
    """ Writes workseet analyses to a CSV file that FIAStar can read.
        Sends the CSV file to the response.
        Requests "TSO2 & F SO2" for all requests.
        uses analysis' PARENT UID as 'Sample name' col.
        uses analysis' CONTAINER UID as 'Sample type' col.
        (they are not always the same; think of multiple duplicates of the same
        analysis.)
    """

    def __call__(self, analyses):
        tray = 1
        now = DateTime().strftime('%Y%m%d-%H%M')
        uc = getToolByName(self.context, 'uid_catalog')
        instrument = self.context.getInstrument()
        norm = getUtility(IIDNormalizer).normalize
        filename  = '%s-%s.csv'%(self.context.getId(),
                                 norm(instrument.getDataInterface()))
        listname  = '%s_%s_%s' %(self.context.getId(),
                                 norm(instrument.Title()), now)
        options = {'dilute_factor' : 1,
                   'method': 'F SO2 & T SO2'}
        for k,v in instrument.getDataInterfaceOptions():
            options[k] = v

        # for looking up "cup" number (= slot) of ARs
        parent_to_slot = {}
        layout = self.context.getLayout()
        for x in range(len(layout)):
            a_uid = layout[x]['analysis_uid']
            p_uid = uc(UID=a_uid)[0].getObject().aq_parent.UID()
            layout[x]['parent_uid'] = p_uid
            if p_uid not in parent_to_slot.keys():
                parent_to_slot[p_uid] = int(layout[x]['position'])

        # write rows, one per PARENT
        header = [listname, options['method']]
        rows = []
        rows.append(header)
        tmprows = []
        ARs_exported = []
        for x in range(len(layout)):
            # create batch header row
            c_uid = layout[x]['container_uid']
            p_uid = layout[x]['parent_uid']
            if p_uid in ARs_exported:
                continue
            cup = parent_to_slot[p_uid]
            tmprows.append([tray,
                            cup,
                            p_uid,
                            c_uid,
                            options['dilute_factor'],
                            ""])
            ARs_exported.append(p_uid)
        tmprows.sort(lambda a,b:cmp(a[1], b[1]))
        rows += tmprows

        ramdisk = StringIO()
        writer = csv.writer(ramdisk, delimiter=';')
        assert(writer)
        writer.writerows(rows)
        result = ramdisk.getvalue()
        ramdisk.close()

        #stream file to browser
        setheader = self.request.RESPONSE.setHeader
        setheader('Content-Length',len(result))
        setheader('Content-Type', 'text/comma-separated-values')
        setheader('Content-Disposition', 'inline; filename=%s' % filename)
        self.request.RESPONSE.write(result)


def Import(context, request):
    """ FOSS FIAStar analysis results
    """
    infile = request.form['data_file']
    fileformat = request.form['format']
    artoapply = request.form['artoapply']
    override = request.form['override']
    instrument = request.form.get('instrument', None)
    errors = []
    logs = []
    warns = []

    # Load the most suitable parser according to file extension/options/etc...
    parser = None
    if not hasattr(infile, 'filename'):
        errors.append(_("No file selected"))
    if fileformat == 'csv':
        parser = FOSSFIAStarCSVParser(infile)
    else:
        errors.append(t(_("Unrecognized file format ${fileformat}",
                          mapping={"fileformat": fileformat})))

    if parser:
        # Load the importer
        status = ['sample_received', 'to_be_verified']
        if artoapply == 'received':
            status = ['sample_received']
        elif artoapply == 'received_tobeverified':
            status = ['sample_received', 'to_be_verified']

        over = [False, False]
        if override == 'nooverride':
            over = [False, False]
        elif override == 'override':
            over = [True, False]
        elif override == 'overrideempty':
            over = [True, True]

        importer = FOSSFIAStarImporter(parser=parser,
                                       context=context,
                                       allowed_ar_states=status,
                                       allowed_analysis_states=None,
                                       override=over,
                                       instrument_uid=instrument)
        tbex = ''
        try:
            importer.process()
        except Exception:
            tbex = traceback.format_exc()
        errors = importer.errors
        logs = importer.logs
        warns = importer.warns
        if tbex:
            errors.append(tbex)

    results = {'errors': errors, 'log': logs, 'warns': warns}

    return json.dumps(results)
