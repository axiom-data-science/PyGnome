'''
tests for geojson outputter
'''
import geojson
import os
import shutil

import numpy as np
import pytest
import geojson

from gnome.outputters import GeoJson
from gnome.spill import SpatialRelease, Spill, point_line_release_spill
from gnome.utilities.time_utils import date_to_sec
from gnome.basic_types import oil_status


basedir = os.path.dirname(__file__)
datadir = os.path.join(basedir, 'sample_data')
output_dir = os.path.join(basedir, 'geojson_output')


@pytest.fixture(scope='function')
def model(sample_model):
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
    os.mkdir(output_dir)

    model = sample_model['model']
    rel_start_pos = sample_model['release_start_pos']
    rel_end_pos = sample_model['release_end_pos']

    model.cache_enabled = True
    model.uncertain = True

    model.outputters += GeoJson(output_dir=output_dir)

    N = 10  # a line of ten points
    line_pos = np.zeros((N, 3), dtype=np.float64)
    line_pos[:, 0] = np.linspace(rel_start_pos[0], rel_end_pos[0], N)
    line_pos[:, 1] = np.linspace(rel_start_pos[1], rel_end_pos[1], N)

    # print start_points

    model.spills += point_line_release_spill(1,
                                             start_position=rel_start_pos,
                                             release_time=model.start_time,
                                             end_position=rel_end_pos)

    release = SpatialRelease(start_position=line_pos,
                           release_time=model.start_time)

    model.spills += Spill(release)

    model.rewind()
    return model


def test_init():
    'simple initialization passes'
    g = GeoJson()
    assert g.output_dir == './'
    assert g.roundto == 4
    assert g.round_data


def test_model_outputgeojson(model):
    'test geojson outputter with a model since simplest to do that'
    model.full_run()
    assert os.path.exists(output_dir)


def test_spill_id_geojson(model):
    'test geojson outputter with a model since simplest to do that'
    # default is to round data
    roundto = model.outputters.get_by_index(0).roundto
    for ix in range(3):
        output = model.step()
        l_id = model.spills.LE('id')
        uncertain = False
        for elem in range(sum(model.spills.num_released)):
            g_elem = output['geojson']['features'][elem]
            match = np.where(l_id == g_elem['id'])[0][0]

            if g_elem['properties']['spill_type'] == 'uncertain':
                uncertain = True

            # time
            assert (date_to_sec(model.spills.LE('current_time_stamp',
                                                uncertain)) ==
                g_elem['properties']['current_time'])

            # check geojson properties match with model arrays
            # (long, lat)
            assert np.allclose(
                model.spills.LE('positions', uncertain)[match, :2],
                g_elem['geometry']['coordinates'], atol=10 ** -roundto)

            # depth
            assert (model.spills.LE('positions', uncertain)[match, 2] ==
                g_elem['properties']['depth'])

            # other properties
            assert (model.spills.LE('status_codes', uncertain)[match] ==
                getattr(oil_status, g_elem['properties']['status_code']))

            assert ix == g_elem['properties']['step_num']

            spill_num = model.spills.LE('spill_num', uncertain)[match]
            assert (model.spills.spill_by_index(spill_num, uncertain).id ==
                g_elem['properties']['spill_id'])
