from pywps import Process
# from pywps import LiteralInput
from pywps import ComplexInput, LiteralInput, ComplexOutput
from pywps import Format, FORMATS
from pywps.app.Common import Metadata

from flyingpigeon.log import init_process_logger
# from flyingpigeon.utils import rename_complexinputs
from flyingpigeon.utils import archive, archiveextract

# from flyingpigeon.datafetch import write_fileinfo
from flyingpigeon.datafetch import fetch_eodata
from flyingpigeon.datafetch import _EODATA_
from flyingpigeon import eodata

import os
from datetime import datetime as dt
from datetime import timedelta, time
from tempfile import mkstemp

import logging
LOGGER = logging.getLogger("PYWPS")


class NdviProcess(Process):
    """
    Normalized Difference Vegetation Index (NDVI)
    """
    def __init__(self):
        inputs = [
            LiteralInput("products", "Earth Observation Product",
                         abstract="Choose Earth Observation Products",
                         default='PlanetScope',
                         data_type='string',
                         min_occurs=1,
                         max_occurs=1,
                         allowed_values=['PlanetScope']
                         ),

            LiteralInput('BBox', 'Bounding Box',
                         data_type='string',
                         abstract="Enter a bbox: min_lon, max_lon, min_lat, max_lat."
                                  " min_lon=Western longitude,"
                                  " max_lon=Eastern longitude,"
                                  " min_lat=Southern or northern latitude,"
                                  " max_lat=Northern or southern latitude."
                                  " For example: -80,50,20,70",
                         min_occurs=1,
                         max_occurs=1,
                         default='14.6,14.8,8.7,8.9',
                         ),

            LiteralInput('start', 'Start Date',
                         data_type='date',
                         abstract='First day of the period to be searched for EO data.'
                                  '(if not set, 30 days befor end of period will be selected',
                         default=(dt.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                         min_occurs=0,
                         max_occurs=1,
                         ),

            LiteralInput('end', 'End Date',
                         data_type='date',
                         abstract='Last day of the period to be searched for EO data.'
                                  '(if not set, current day is set.)',
                         default=dt.now().strftime('%Y-%m-%d'),
                         min_occurs=0,
                         max_occurs=1,
                         ),

            LiteralInput('token', 'Authentification',
                         data_type='string',
                         abstract='Authentification token generated by Planet Earth Observation Explorer.',
                         # default='2013-12-31',
                         min_occurs=1,
                         max_occurs=1,
                         ),

            LiteralInput("archive_format", "Archive format",
                         abstract="Result files will be compressed into archives.\
                                  Choose an appropriate format",
                         default="tar",
                         data_type='string',
                         min_occurs=1,
                         max_occurs=1,
                         allowed_values=['zip', 'tar']
                         )

            #
            # ComplexInput('resource', 'Resource',
            #              abstract="NetCDF Files or archive (tar/zip) containing netCDF files.",
            #              min_occurs=1,
            #              max_occurs=1000,
            #              #  maxmegabites=5000,
            #              supported_formats=[Format('application/x-netcdf'),
            #                                 Format('application/x-tar'),
            #                                 Format('application/zip'),
            #                                 ]
            #              )
        ]

        outputs = [
            ComplexOutput("ndvi_archive", "geotif files",
                          abstract="Archive (tar/zip) containing NDVI result files",
                          supported_formats=[Format('application/x-tar'),
                                             Format('application/zip')
                                             ],
                          as_reference=True,
                          ),

            ComplexOutput("plot_archive", "png files",
                          abstract="Archive (tar/zip) containing NDVI result files",
                          supported_formats=[Format('application/x-tar'),
                                             Format('application/zip')
                                             ],
                          as_reference=True,
                          ),

            ComplexOutput('ndviexample', 'Example graphic',
                          abstract="Example plot of one of the resultes for quickcheck purpose.",
                          as_reference=True,
                          supported_formats=[Format('image/png')]
                          ),

            ComplexOutput("output_log", "Logging information",
                          abstract="Collected logs during process run.",
                          supported_formats=[Format("text/plain")],
                          as_reference=True,
                          )
        ]

        super(NdviProcess, self).__init__(
            self._handler,
            identifier="EO_ndvi",
            title="EO NDVI",
            version="0.1",
            abstract="Normalized Difference Vegetation Index (NDVI),"
                     "developed by a NASA scientist named Compton Tucker in 1977,"
                     "is commonly used to assess whether an area contains live green vegetation or not."
                     "It can show the difference between water and plants, bare soil and grass,"
                     "whether plants are under stress, and what lifecycle stage a crop is in",
            metadata=[
                Metadata('Documentation', 'http://flyingpigeon.readthedocs.io/en/latest/'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True,
        )

    def _handler(self, request, response):
        response.update_status("start fetch data", 10)

        init_process_logger('log.txt')
        response.outputs['output_log'].file = 'log.txt'

        products = [inpt.data for inpt in request.inputs['products']]

        bbox = []  # order xmin ymin xmax ymax
        bboxStr = request.inputs['BBox'][0].data
        bboxStr = bboxStr.split(',')
        bbox.append(float(bboxStr[0]))
        bbox.append(float(bboxStr[2]))
        bbox.append(float(bboxStr[1]))
        bbox.append(float(bboxStr[3]))

        if 'end' in request.inputs:
            end = request.inputs['end'][0].data
            end = dt.combine(end, time(23, 59, 59))
        else:
            end = dt.now()

        if 'start' in request.inputs:
            start = request.inputs['start'][0].data
            start = dt.combine(start, time(0, 0, 0))
        else:
            start = end - timedelta(days=30)

        if (start > end):
            start = dt.now() - timedelta(days=30)
            end = dt.now()
            LOGGER.exception("periode end befor periode start, period is set to the last 30 days from now")

        token = request.inputs['token'][0].data
        archive_format = request.inputs['archive_format'][0].data

        resources = []

        # resources_sleeping = []
        for product in products:
            if product == 'PlanetScope':
                item_type = 'PSScene4Band'
                assets = ['analytic', 'analytic_xml']
                for asset in assets:
                    LOGGER.debug('itym type: %s , asset: %s' % (item_type, asset))
                    fetch_sleep, tiles = fetch_eodata(item_type,
                                                      asset,
                                                      token,
                                                      bbox,
                                                      period=[start, end],
                                                      cloud_cover=0.5,
                                                      cache=True)
                    resources.extend(tiles)
                    # resources_sleeping.extend(fetch_sleep)
                response.update_status("calculating the NDVI ", 30)
                try:
                    LOGGER.debug('Start calculating NDVI')
                    ndvi_tiles, ndvi_plots = eodata.ndvi(tiles, product)
                    # ndvi_merged = eodata.merge(ndvi_tiles)
                except:
                    LOGGER.exception('failed to calculate NDVI')
        try:
            ndvi_archive = archive(ndvi_tiles, format=archive_format)
            LOGGER.info('geotiff files added to archive')
        except:
            msg = 'failed adding species_files indices to archive'
            LOGGER.exception(msg)

        response.outputs['ndvi_archive'].file = ndvi_archive

        try:
            plot_archive = archive(ndvi_plots, format=archive_format)
            LOGGER.info('png files added to archive')
        except:
            msg = 'failed adding species_files indices to archive'
            LOGGER.exception(msg)

        response.outputs['plot_archive'].file = plot_archive


        i = next((i for i, x in enumerate(ndvi_plots) if x), None)
        if i is None:
            response.outputs['ndviexample'].file = "dummy.png"
        else:
            response.outputs['ndviexample'].file = ndvi_plots[i]

        response.update_status("done", 100)

        return response
