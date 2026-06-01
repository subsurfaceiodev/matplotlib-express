import re


def plotly_to_mpl_marker(marker_symbol: str):
    return {
        'circle': 'o', 'square': 's', 'diamond': 'D', 'cross': 'P', 'x': 'X', 'triangle-up': '^',
        'triangle-down': 'v', 'triangle-left': '<', 'triangle-right': '>', 'triangle-ne': None,
        'triangle-se': None, 'triangle-sw': None, 'triangle-nw': None, 'pentagon': 'p', 'hexagon': 'h',
        'hexagon2': 'H', 'octagon': '8', 'star': '*', 'hexagram': None, 'star-triangle-up': None,
        'star-triangle-down': None, 'star-square': None, 'star-diamond': None, 'diamond-tall': 'd',
        'diamond-wide': None, 'hourglass': None, 'bowtie': None, 'circle-cross': None, 'circle-x': None,
        'square-cross': None, 'square-x': None, 'diamond-cross': None, 'diamond-x': None, 'cross-thin': '+',
        'x-thin': 'x', 'asterisk': None, 'hash': None, 'y-up': '2', 'y-down': '1', 'y-left': '3',
        'y-right': '4', 'line-ew': '_', 'line-ns': '|', 'line-ne': None, 'line-nw': None, 'arrow-up': None,
        'arrow-down': None, 'arrow-left': None, 'arrow-right': None, 'arrow-bar-up': None,
        'arrow-bar-down': None, 'arrow-bar-left': None, 'arrow-bar-right': None
    }[marker_symbol]


def _parse_plotly_dash(
        dash_string,
        base_unit=1.0
):
    # TODO needs more work
    # Clean up the string and split it
    dash_string = dash_string.strip().replace('px', '').replace(',', ' ')
    parts = re.findall(r"[\d.]+%?|[\d.]+", dash_string)

    pattern = []
    for part in parts:
        if "%" in part:
            # Convert percentage to a scaled length
            percentage = float(part.strip('%'))
            pattern.append(base_unit * (percentage / 100))
        else:
            # Assume it's in pixels or absolute value
            pattern.append(float(part))

    return 0, pattern


def plotly_to_mpl_linestyle(line_dash: str | None):
    mapping = {
        'solid': 'solid',
        'dot': 'dotted',
        'dash': 'dashed',
        'longdash': (0, (5, 10)),
        'dashdot': 'dashdot',
        'longdashdot': (0, (9, 2, 1, 2)),
    }
    if line_dash and line_dash in mapping:
        linestyle = mapping[line_dash]
    elif line_dash and ',' in line_dash:
        linestyle = _parse_plotly_dash(line_dash)
    else:
        linestyle = None
    return linestyle


def plotly_to_mpl_drawstyle(line_shape: str):
    raise {
        'linear': 'default',
        'spline': None,
        'hv': 'steps-post',
        'vh': 'steps-pre',
        'hvh': None,
        'vhv': 'steps-mid',
    }[line_shape]


def plotly_to_mpl_markersize(marker_size: float):
    # TODO may need conversion
    #  see mpl_express_core conversion
    return marker_size


def plotly_to_mpl_linewidth(line_width: float):
    return line_width * 0.75
