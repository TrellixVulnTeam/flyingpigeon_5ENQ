import logging

<<<<<<< HEAD
=======
from flyingpigeon.log import init_process_logger
from flyingpigeon.ocgis_module import call
from flyingpigeon.utils import archive, archiveextract
from flyingpigeon.utils import rename_complexinputs
from flyingpigeon.utils import sort_by_filename, get_values, get_time
>>>>>>> 19815922c9b8e810550156a12b0c458b221d7c41
from numpy import savetxt, column_stack
from pywps import ComplexInput, ComplexOutput
from pywps import Format
from pywps import LiteralInput
from pywps import Process
from pywps.app.Common import Metadata
from shapely.geometry import Point

<<<<<<< HEAD
# from eggshell.log import init_process_logger
from flyingpigeon.log import init_process_logger
from flyingpigeon.ocgis_module import call
from flyingpigeon.utils import archive, archiveextract
from flyingpigeon.utils import rename_complexinputs
from flyingpigeon.utils import sort_by_filename, get_values, get_time

=======
>>>>>>> 19815922c9b8e810550156a12b0c458b221d7c41
LOGGER = logging.getLogger("PYWPS")


class PointinspectionProcess(Process):
    """
    TODO: optionally provide point list as file (csv, geojson) and WFS service
    """

    def __init__(self):
        inputs = [
            ComplexInput('resource', 'Resource',
                         abstract='NetCDF Files or archive (tar/zip) containing NetCDF files.',
                         min_occurs=1,
                         max_occurs=1000,
                         supported_formats=[
                             Format('application/x-netcdf'),
                             Format('application/x-tar'),
                             Format('application/zip'),
                         ]),

            LiteralInput("coords", "Coordinates",
                         abstract="A comma-seperated tuple of WGS85 lon,lat decimal coordinates (e.g. 2.356138, 48.846450)",
                         # noqa
                         default="2.356138, 48.846450",
                         data_type='string',
                         min_occurs=1,
                         max_occurs=100,
                         ),
        ]
        outputs = [
            ComplexOutput('output_log', 'Logging information',
                          abstract="Collected logs during process run.",
                          as_reference=True,
                          supported_formats=[Format('text/plain')]
                          ),

            ComplexOutput('tarout', 'Subsets',
                          abstract="Tar archive containing one CSV file per input file, each one storing time series column-wise for all point coordinates.",
                          as_reference=True,
                          supported_formats=[Format('application/x-tar')]
                          ),
        ]

        super(PointinspectionProcess, self).__init__(
            self._handler,
            identifier="pointinspection",
            title="Point Inspection",
            abstract='Extract the timeseries at the given coordinates.',
            version="0.10",
            metadata=[
                Metadata('LSCE', 'http://www.lsce.ipsl.fr/en/index.php'),
                Metadata('Doc', 'http://flyingpigeon.readthedocs.io/en/latest/'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True,
        )

    def _handler(self, request, response):
        init_process_logger('log.txt')
        response.outputs['output_log'].file = 'log.txt'

        ncs = archiveextract(
            resource=rename_complexinputs(request.inputs['resource']))
        LOGGER.info('ncs: {}'.format(ncs))

        coords = []
        for coord in request.inputs['coords']:
            coords.append(coord.data)

        LOGGER.info('coords {}'.format(coords))
        filenames = []
        nc_exp = sort_by_filename(ncs, historical_concatination=True)

        for key in nc_exp.keys():
            try:
                LOGGER.info('start calculation for {}'.format(key))
                ncs = nc_exp[key]
                times = get_time(ncs)  # , format='%Y-%m-%d_%H:%M:%S')
                concat_vals = times  # ['%s-%02d-%02d_%02d:%02d:%02d' %
                # (t.year, t.month, t.day, t.hour, t.minute, t.second) for t in times]
                header = 'date_time'
                filename = '{}.csv'.format(key)
                filenames.append(filename)

                for p in coords:
                    try:
                        response.update_status('processing point: {}'.format(p), 20)
                        # define the point:
                        p = p.split(',')
                        point = Point(float(p[0]), float(p[1]))

                        # get the values
                        timeseries = call(resource=ncs, geom=point, select_nearest=True)
                        vals = get_values(timeseries)

                        # concatenation of values
                        header = header + ',{}-{}'.format(p[0], p[1])
                        concat_vals = column_stack([concat_vals, vals])
                    except Exception as e:
                        LOGGER.debug('failed for point {} {}'.format(p, e))
                response.update_status('*** all points processed for {0} ****'.format(key), 50)

                # TODO: Ascertain whether this 'savetxt' is a valid command without string formatting argument: '%s'
                savetxt(filename, concat_vals, fmt='%s', delimiter=',', header=header)
            except Exception as ex:
                LOGGER.debug('failed for {}: {}'.format(key, str(ex)))

        # set the outputs
        response.update_status('*** creating output tar archive ****', 90)
        tarout_file = archive(filenames)
        response.outputs['tarout'].file = tarout_file
        return response
