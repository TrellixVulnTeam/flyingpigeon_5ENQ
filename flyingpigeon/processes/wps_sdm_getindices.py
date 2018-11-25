"""
Processes for Species distribution
Author: Nils Hempelmann , Wolfgang Falk
"""

import logging

from pywps import ComplexInput, ComplexOutput
from pywps import Format
from pywps import LiteralInput
from pywps import Process
from pywps.app.Common import Metadata

from flyingpigeon import sdm
from flyingpigeon.utils import archive, archiveextract, sort_by_filename
from eggshell.log import init_process_logger

from flyingpigeon.sdm import _SDMINDICES_
from flyingpigeon.utils import archive, archiveextract

from flyingpigeon.utils import rename_complexinputs

LOGGER = logging.getLogger("PYWPS")


class SDMgetindicesProcess(Process):
    def __init__(self):
        inputs = [
            ComplexInput('resource', 'Resource',
                         abstract='NetCDF Files or archive (tar/zip) containing netCDF files.',
                         metadata=[Metadata('Info')],
                         min_occurs=1,
                         max_occurs=1000,
                         supported_formats=[
                             Format('application/x-netcdf'),
                             Format('application/x-tar'),
                             Format('application/zip'),
                         ]),

            LiteralInput("indices", "Indices",
                         abstract="Climate indices related to growth conditions \
                                    of tree species",
                         default='TG_JJA',
                         data_type='string',
                         min_occurs=1,
                         max_occurs=10,
                         allowed_values=_SDMINDICES_
                         ),

            LiteralInput("archive_format", "Archive format",
                         abstract="Result files will be compressed into archives. \
                                   Choose an appropriate format",
                         default="tar",
                         data_type='string',
                         min_occurs=1,
                         max_occurs=1,
                         allowed_values=['zip', 'tar']
                         )
        ]

        outputs = [
            ComplexOutput("output_indices", "Climate indices for growth conditions over all timesteps",
                          abstract="Archive (tar/zip) containing calculated climate indices",
                          supported_formats=[Format('application/x-tar'),
                                             Format('application/zip')
                                             ],
                          as_reference=True,
                          ),

            ComplexOutput('ncout', 'Subsets for one resource',
                          abstract="NetCDF file with subsets of one resource.",
                          as_reference=True,
                          supported_formats=[Format('application/x-netcdf')]
                          ),

            ComplexOutput('output_log', 'Logging information',
                          abstract="Collected logs during process run.",
                          as_reference=True,
                          supported_formats=[Format('text/plain')]
                          )
        ]

        super(SDMgetindicesProcess, self).__init__(
            self._handler,
            identifier="sdm_getindices",
            title="Species distribution Model (only indices calculation )",
            version="0.10",
            metadata=[
                Metadata("LWF", "http://www.lwf.bayern.de/"),
                Metadata(
                    "Doc",
                    "http://flyingpigeon.readthedocs.io/en/latest/descriptions/index.html#species-distribution-model"),
                Metadata("paper",
                         "http://www.hindawi.com/journals/jcli/2013/787250/"),
                Metadata("Tutorial",
                         "http://flyingpigeon.readthedocs.io/en/latest/tutorials/sdm.html"),
            ],
            abstract="Indices preparation for SDM process",
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True,
        )

    def _handler(self, request, response):

        init_process_logger('log.txt')
        response.outputs['output_log'].file = 'log.txt'

        response.update_status('Start process', 0)

        try:
            LOGGER.info('reading the arguments')
            resources = archiveextract(
                resource=rename_complexinputs(request.inputs['resource']))
            indices = [inpt.data for inpt in request.inputs['indices']]
            LOGGER.debug("indices = {}".format(indices))
            archive_format = request.inputs['archive_format'][0].data
        except Exception as ex:
            msg = 'failed to read the arguments: {}'.format(str(ex))
            LOGGER.exception(msg)
            raise Exception(msg)
        LOGGER.info('indices {}'.format(indices))

        #################################
        # calculate the climate indices
        #################################

        # indices calculation
        try:
            response.update_status('calculation of indices', 30)
            ncs_indices = sdm.get_indices(resource=resources, indices=indices)
            LOGGER.info('indice calculation done')
        except Exception as ex:
            # TODO: 'ds_name' does not resolve. What is this referring to? This will throw a critical error!
            msg = 'indice calculation failed for {}: {}'.format(ds_name, str(ex))
            LOGGER.exception(msg)
            raise Exception(msg)

        # archive multiple output files to one archive file
        try:
            archive_indices = archive(ncs_indices, format=archive_format)
            LOGGER.info('indices 3D added to tarfile')
        except Exception as ex:
            msg = 'failed adding indices to tar: {}'.format(str(ex))
            LOGGER.exception(msg)
            raise Exception(msg)

        response.outputs['output_indices'].file = archive_indices

        i = next((i for i, x in enumerate(ncs_indices) if x), None)
        response.outputs['ncout'].file = ncs_indices[i]

        response.update_status('done', 100)
        return response
