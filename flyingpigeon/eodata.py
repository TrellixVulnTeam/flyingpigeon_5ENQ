from tempfile import mkstemp

import logging
LOGGER = logging.getLogger("PYWPS")


def merge(tiles):
    from flyingpigeon import gdal_merge as gm
    from os.path import join, basename
    import sys

    merged_tiles = []
    dates = set()
    dates = dates.union([basename(pic).split('_')[0] for pic in tiles])

    for date in dates:
        try:
            LOGGER.debug('merge date %s' % date)
            _, filename = mkstemp(dir='.', prefix=date, suffix='.tif')
            call = ['-o',  filename]
            tiles_day = [tile for tile in tiles if date in tile]

            for tile_d in tiles_day:
                call.extend([tile_d])
            sys.argv[1:] = call
            gm.main()

            merged_tiles.extend([filename])
            LOGGER.debug("files merged for date %s" % date)
        except:
            LOGGER.exception("failed to merge tiles of date  %s " % date)

    return merged_tiles


def ndvi_sorttiles(tiles, product="PSScene"):
    """
    sort un list fo files to calculate the NDVI.
    red nivr and metadata are sorted in an dictionary

    :param tiles: list of scene files and metadata
    :param product: EO data product e.g. "PSScene" (default)

    :return dictionary: sorted files ordered in a dictionary
    """

    from os.path import splitext, basename
    if product == "PSScene":
        ids = []
        for tile in tiles:
            bn, _ = splitext(basename(tile))
            ids.extend([bn])

        tiles_dic = {key: None for key in ids}

        for key in tiles_dic.keys():
            tm = [t for t in tiles if key in t]
            tiles_dic[key] = tm

    return tiles_dic


def ndvi(tiles, product='PlanetScope'):
    """
    :param tiles: list of tiles including appropriate metadata files
    :param product: EO product e.g. "PlanetScope" (default)

    :retrun files, plots : list of calculated files and plots
    """

    import rasterio
    import numpy

    ndvifiles = []
    ndviplots = []

    if product == 'PlanetScope':
        tiles_dic = ndvi_sorttiles(tiles, product=product)
        for key in tiles_dic.keys():

            tile = next(x for x in tiles_dic[key] if ".tif" in x)
            meta = next(x for x in tiles_dic[key] if ".xml" in x)

            # Load red and NIR bands - note all PlanetScope 4-band images have band order BGRN
            with rasterio.open(tile) as src:
                band_red = src.read(3)

            with rasterio.open(tile) as src:
                band_nir = src.read(4)

            from xml.dom import minidom

            xmldoc = minidom.parse(meta)
            nodes = xmldoc.getElementsByTagName("ps:bandSpecificMetadata")

            # XML parser refers to bands by numbers 1-4
            coeffs = {}
            for node in nodes:
                bn = node.getElementsByTagName("ps:bandNumber")[0].firstChild.data
                if bn in ['1', '2', '3', '4']:
                    i = int(bn)
                    value = node.getElementsByTagName("ps:reflectanceCoefficient")[0].firstChild.data
                    coeffs[i] = float(value)

            # Multiply by corresponding coefficients
            band_red = band_red * coeffs[3]
            band_nir = band_nir * coeffs[4]

            # Allow division by zero
            numpy.seterr(divide='ignore', invalid='ignore')

            # Calculate NDVI
            ndvi = (band_nir.astype(float) - band_red.astype(float)) / (band_nir + band_red)

            # Set spatial characteristics of the output object to mirror the input
            kwargs = src.meta
            kwargs.update(
                dtype=rasterio.float32,
                count=1)

            # Create the file
            _, ndvifile = mkstemp(dir='.', prefix="ndvi_%s" % key, suffix='.tif')
            with rasterio.open(ndvifile, 'w', **kwargs) as dst:
                    dst.write_band(1, ndvi.astype(rasterio.float32))

            _, ndviplot = mkstemp(dir='.', prefix="ndvi_%s" % key, suffix='.png')
            import matplotlib.pyplot as plt
            plt.imsave(ndviplot, ndvi, cmap=plt.cm.summer)

            ndvifiles.extend([ndvifile])
            ndviplots.extend([ndviplot])

    return ndvifiles, ndviplots
