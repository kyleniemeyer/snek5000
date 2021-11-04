import tempfile
from io import StringIO
from pathlib import Path

from snek5000.log import logger
from snek5000.params import Parameters
from snek5000.util import init_params


def test_empty_params():
    params = Parameters(tag="empty")
    params._write_par()


def test_simul_params():
    from snek5000.solvers.base import Simul

    params = Simul.create_default_params()

    buffer = StringIO()
    params.nek._write_par(buffer)

    buffer1 = StringIO(buffer.getvalue())
    params.nek._read_par(buffer1)

    buffer2 = StringIO()
    params.nek._write_par(buffer2)

    assert buffer.getvalue() == buffer2.getvalue()


def test_oper_params(oper):
    from snek5000.operators import Operators

    params = init_params(Operators)
    logger.debug(params.oper.max)
    logger.debug(params.oper.max._doc)
    logger.debug(params.oper.elem)
    logger.debug(params.oper.elem._doc)


def test_par_xml_match():
    from phill.solver import Simul

    params = Simul.create_default_params()
    output1 = StringIO()
    params.nek._write_par(output1)

    tmp_dir = Path(tempfile.mkdtemp("snek5000", __name__))
    params_xml = params._save_as_xml(str(tmp_dir / "params_simul.xml"))

    try:
        from snek5000.params import Parameters

        nparams = Parameters(tag="params", path_file=params_xml)
    except ValueError:
        # NOTE: used to raise an error, now testing experimentally
        pass
    #  else:
    #      raise ValueError("Parameters(path_file=...) worked unexpectedly.")

    nparams = Simul.load_params_from_file(path_xml=params_xml)
    output2 = StringIO()
    nparams.nek._write_par(output2)

    par1 = output1.getvalue()
    par2 = output2.getvalue()
    output1.close()
    output2.close()

    def format_sections(params):
        par = params.nek._par_file

        # no options in the section
        for section_name in par.sections():
            if not par.options(section_name):
                par.remove_section(section_name)

        return sorted(par.sections())

    assert format_sections(params) == format_sections(nparams)

    def format_par(text):
        """Sort non-blank lines"""
        from ast import literal_eval

        ftext = []
        for line in text.splitlines():
            # not blank
            if line:
                # Uniform format for literals
                if " = " in line:
                    key, value = line.split(" = ")
                    try:
                        line = " = ".join([key, str(literal_eval(value))])
                    except (SyntaxError, ValueError):
                        pass

                ftext.append(line)

        return sorted(ftext)

    assert format_par(par1) == format_par(par2)


def test_user_params():
    def complete_create_default_params(p):
        p._set_attribs({"prandtl": 0.71, "rayleigh": 1.8e8})
        p._record_nek_user_params({"prandtl": 8, "rayleigh": 9})
        p._set_child("output")
        p.output._set_child("other", {"write_interval": 100})
        p.output.other._record_nek_user_params({"write_interval": 1}, overwrite=True)

    from snek5000.solvers.base import Simul

    params = Simul.create_default_params()

    if hasattr(params.nek.general, "_recorded_user_params"):
        params.nek.general._recorded_user_params.clear()

    complete_create_default_params(params)

    assert params.nek.general._recorded_user_params == {
        8: "prandtl",
        9: "rayleigh",
        1: "output.other.write_interval",
    }

    params.prandtl = 2
    params.rayleigh = 2e8
    params.output.other.write_interval = 1000

    buffer = StringIO()
    params.nek._write_par(buffer)

    params1 = Simul.create_default_params()
    complete_create_default_params(params1)
    buffer1 = StringIO(buffer.getvalue())
    params1.nek._read_par(buffer1)

    assert params1.prandtl == params.prandtl
    assert params1.rayleigh == params.rayleigh
    assert params1.output.other.write_interval == params.output.other.write_interval
