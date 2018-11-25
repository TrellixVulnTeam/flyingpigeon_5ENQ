from pywps import Service
from pywps.tests import assert_response_success

from flyingpigeon.processes import ClipcontinentProcess
from flyingpigeon.tests.common import TESTDATA, client_for, CFG_FILE, get_output
import os


datainputs_fmt = (
    "resource=files@xlink:href={0};"
    "region={1};"
    "mosaic={2};"
)


def test_wps_subset_continents():
    client = client_for(
        Service(processes=[ClipcontinentProcess()], cfgfiles=CFG_FILE))

    datainputs = datainputs_fmt.format(
        TESTDATA['cmip5_tasmax_2006_nc'],
        'Africa',
        "True",)

    resp = client.get(
        service='wps', request='execute', version='1.0.0',
        identifier='subset_continents',
        datainputs=datainputs)

    assert_response_success(resp)

    # Check output file size is smaller than input.
    out = get_output(resp.xml)
    ins = os.path.getsize(TESTDATA['cmip5_tasmax_2006_nc'][6:])
    outs = os.path.getsize(out['ncout'][6:])
    assert (outs < ins)
