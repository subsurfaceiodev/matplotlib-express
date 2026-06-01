import re
import mpltern  # noqa: F401
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import datetime
import plotly
import numpy as np
from collections import defaultdict
from plotly.express._core import *  # noqa
from plotly._subplots import (
    _subplot_type_for_trace_type,
)
from .utils import fig_legend
from .converters import (
    plotly_to_mpl_marker,
    plotly_to_mpl_linestyle,
    plotly_to_mpl_drawstyle
)

PPI = 96


def configure_ternary_axes(args, axs, orders):
    for ax in axs.flatten():
        ax.set(
            tlabel=get_label(args, args["a"]),
            llabel=get_label(args, args["b"]),
            rlabel=get_label(args, args["c"]),
        )
        position = 'tick2'
        ax.taxis.set_ticks_position(position)
        ax.laxis.set_ticks_position(position)
        ax.raxis.set_ticks_position(position)

        ax.taxis.set_label_position(position)
        ax.laxis.set_label_position(position)
        ax.raxis.set_label_position(position)

        ax.taxis.set_major_locator(MultipleLocator(10))
        ax.laxis.set_major_locator(MultipleLocator(10))
        ax.raxis.set_major_locator(MultipleLocator(10))


def configure_axes(args, constructor, axs, orders):
    configurators = {
        go.Scatter3d: configure_3d_axes,
        go.Scatterternary: configure_ternary_axes,
        go.Scatterpolar: configure_polar_axes,
        go.Scatterpolargl: configure_polar_axes,
        go.Barpolar: configure_polar_axes,
        go.Scattermap: configure_map,
        go.Choroplethmap: configure_map,
        go.Densitymap: configure_map,
        go.Scattermapbox: configure_mapbox,
        go.Choroplethmapbox: configure_mapbox,
        go.Densitymapbox: configure_mapbox,
        go.Scattergeo: configure_geo,
        go.Choropleth: configure_geo,
    }
    for c in cartesians:
        configurators[c] = configure_cartesian_axes
    if constructor in configurators:
        configurators[constructor](args, axs, orders)


def set_categorical_axis(args, axis, letter, cats):
    if letter == 'x':
        values_versus = args['data_frame'][args['y']]
        sentinel, = axis.plot(
            cats,
            np.linspace(
                min(values_versus),
                max(values_versus),
                len(cats))
        )
    else:
        values_versus = args['data_frame'][args['x']]
        sentinel, = axis.plot(
            np.linspace(
                min(values_versus),
                max(values_versus),
                len(cats)),
            list(reversed(cats)),  # top down for Y axis
        )
    sentinel.remove()
    axis.relim()


def set_cartesian_axis_opts(args, axis, letter, orders):
    if args[letter] in orders:
        # keeps categories order https://stackoverflow.com/a/54593841/10315746
        cats = orders[args[letter]]
        set_categorical_axis(args, axis, letter, cats)

    log_key = "log_" + letter
    range_key = "range_" + letter
    if log_key in args and args[log_key]:
        getattr(axis, f'set_{letter}scale')('log')
        if range_key in args and args[range_key]:
            range_ = args[range_key]
            if not (range_ == [None, None] or range_ == (None, None)):
                getattr(axis, f'set_{letter}lim')(args[range_key])
    elif range_key in args and args[range_key]:
        range_ = args[range_key]
        if not (range_ == [None, None] or range_ == (None, None)):
            getattr(axis, f'set_{letter}lim')(range_)


def get_base_label(axs, letter):
    for ax in axs:
        for text_obj in ax.texts:
            if letter == 'x' and text_obj.get_gid() == 'secondary-x-label':
                return text_obj.get_text()
            if letter == 'y' and text_obj.get_gid() == 'secondary-y-label':
                return text_obj.get_text()
    return ''


def configure_cartesian_axes(args, axs, orders):
    if ("marginal_x" in args and args["marginal_x"]) or (
            "marginal_y" in args and args["marginal_y"]
    ):
        configure_cartesian_marginal_axes(args, axs, orders)
        return

    x_title = get_decorated_label(args, args["x"], "x")
    y_title = get_decorated_label(args, args["y"], "y")
    # Set axis titles and axis options
    for ax in axs.flatten():
        if ax in axs[-1, :]:
            # Set x-axis title in the bottom-most row
            if "is_timeline" not in args:
                ax.set(xlabel=x_title)
        if ax in axs[:, 0]:
            # Set y-axis title in the left-most column
            ax.set(ylabel=y_title)
        set_cartesian_axis_opts(args, ax, "x", orders)
        set_cartesian_axis_opts(args, ax, "y", orders)

    if x_title == 'value':
        orders_letter = 'x'
    else:
        orders_letter = 'y'

    # iterate over columns of each axs rows
    for i in range(axs.shape[0]):
        # flipped because sec axis are places right most
        base_label = get_base_label(np.flip(axs[i, :]), 'y')
        if base_label.startswith('variable='):
            label = base_label.removeprefix('variable=')
            if label in orders:
                cats = orders[label]
                for ax in axs[i, :]:
                    set_categorical_axis(args, ax, orders_letter, cats)

    # iterate over rows of each axs columns
    for i in range(axs.shape[1]):
        base_label = get_base_label(axs[:, i], 'x')
        if base_label.startswith('variable='):
            label = base_label.removeprefix('variable=')
            if label in orders:
                cats = orders[label]
                for ax in axs[:, i]:
                    set_categorical_axis(args, ax, orders_letter, cats)

    # Configure axis type across all x-axes
    if "log_x" in args and args["log_x"]:
        plt.setp(axs, xscale="log")

    # Configure axis type across all y-axes
    if "log_y" in args and args["log_y"]:
        plt.setp(axs, yscale="log")

    # if "is_timeline" in args:
    #     fig.update_xaxes(type="date")

    if "ecdfmode" in args:
        if args["orientation"] == "v":
            plt.setp(axs, yscale=(0, None))
        else:
            plt.setp(axs, xscale=(0, None))


def init_figure(args, subplot_type, frame_list, nrows, ncols, col_labels, row_labels):
    # Build subplot specs
    specs = [[dict(type=subplot_type or "domain")] * ncols for _ in range(nrows)]

    # Default row/column widths uniform
    column_widths = [1.0] * ncols
    row_heights = [1.0] * nrows
    facet_col_wrap = args.get("facet_col_wrap", 0)

    # Build column_widths/row_heights
    if subplot_type == "xy":
        if args.get("marginal_x") is not None:
            if args["marginal_x"] == "histogram" or ("color" in args and args["color"]):
                main_size = 0.74
            else:
                main_size = 0.84

            row_heights = [main_size] * (nrows - 1) + [1 - main_size]
            vertical_spacing = 0.01
        elif facet_col_wrap:
            vertical_spacing = args.get("facet_row_spacing") or 0.07
        else:
            vertical_spacing = args.get("facet_row_spacing") or 0.03

        if args.get("marginal_y") is not None:
            if args["marginal_y"] == "histogram" or ("color" in args and args["color"]):
                main_size = 0.74
            else:
                main_size = 0.84

            column_widths = [main_size] * (ncols - 1) + [1 - main_size]
            horizontal_spacing = 0.005
        else:
            horizontal_spacing = args.get("facet_col_spacing") or 0.02
    else:
        # Other subplot types:
        #   'scene', 'geo', 'polar', 'ternary', 'mapbox', 'domain', None
        #
        # We can customize subplot spacing per type once we enable faceting
        # for all plot types
        if facet_col_wrap:
            vertical_spacing = args.get("facet_row_spacing") or 0.07
        else:
            vertical_spacing = args.get("facet_row_spacing") or 0.03
        horizontal_spacing = args.get("facet_col_spacing") or 0.02

    def _spacing_error_translator(e, direction, facet_arg):
        """
        Translates the spacing errors thrown by the underlying make_subplots
        routine into one that describes an argument adjustable through px.
        """
        if ("%s spacing" % (direction,)) in e.args[0]:
            e.args = (
                e.args[0]
                + """
Use the {facet_arg} argument to adjust this spacing.""".format(
                    facet_arg=facet_arg
                ),
            )
            raise e

    # Create figure with subplots
    try:
        if subplot_type == 'ternary':
            fig, axs = plt.subplots(
                nrows,
                ncols,
                # specs=specs,
                gridspec_kw=dict(
                    wspace=horizontal_spacing,
                    hspace=vertical_spacing,
                ),
                height_ratios=row_heights,
                width_ratios=column_widths,
                subplot_kw=dict(
                    projection='ternary',
                    ternary_sum=100
                ),
                squeeze=False,
            )
        else:
            fig, axs = plt.subplots(
                nrows,
                ncols,
                # specs=specs,
                sharex=args.get('sharex', True),
                sharey=args.get('sharey', True),
                gridspec_kw=dict(
                    wspace=horizontal_spacing,
                    hspace=vertical_spacing,
                ),
                height_ratios=row_heights,
                width_ratios=column_widths,
                squeeze=False,
            )
        row_titles = [] if facet_col_wrap else row_labels
        column_titles = [] if facet_col_wrap else col_labels
        subplot_titles = col_labels if facet_col_wrap else []
        for ax, row_title in zip(
                axs[:, -1],
                row_titles
        ):
            ax.annotate(
                row_title,
                xy=(1.0, 0.5),
                xycoords='axes fraction',
                xytext=(10, 0),
                textcoords='offset points',
                ha='center',
                va='center',
                rotation=-90,
                gid='secondary-y-label'
            )
        for ax, column_title in zip(
                axs[0, :],
                column_titles
        ):
            ax.annotate(
                column_title,
                xy=(0.5, 1.0),
                xycoords='axes fraction',
                xytext=(0, 10),
                textcoords='offset points',
                ha='center',
                gid='secondary-x-label'
            )
        for ax, subplot_title in zip(
                axs.flatten(),
                subplot_titles
        ):
            ax.set(
                title=subplot_title,
            )

    except ValueError as e:
        _spacing_error_translator(e, "Horizontal", "facet_col_spacing")
        _spacing_error_translator(e, "Vertical", "facet_row_spacing")

    # Remove explicit font size of row/col titles so template can take over
    # for annot in fig.layout.annotations:
    #     annot.update(font=None)

    return fig, axs


def handle_xy_arrays(x, y):
    # tries to mimic plotly behaviour

    def has_str(array):
        return any(isinstance(item, str) for item in array)

    def get_null_flag(array):
        return [item is None or (isinstance(item, float) and bool(np.isnan(item))) for item in array]

    # ideally None as np.nan should be applied where
    # any trace in axis has str, but seems to be safe
    # to apply in all cases
    x = np.where(np.equal(x, None), np.nan, x)
    y = np.where(np.equal(y, None), np.nan, y)

    x_has_str = has_str(x)
    y_has_str = has_str(y)

    if x_has_str and y_has_str:
        x = x.astype(str)
        y = y.astype(str)
        return x, y

    if x_has_str:
        null_flag = get_null_flag(x)
        y = np.where(null_flag, None, y)
        x = x.astype(str)
    elif y_has_str:
        null_flag = get_null_flag(y)
        x = np.where(null_flag, None, x)
        y = y.astype(str)
    return x, y


def make_figure(args, constructor, trace_patch=None, layout_patch=None):
    trace_patch = trace_patch or {}
    layout_patch = layout_patch or {}
    apply_default_cascade(args, constructor=constructor)

    args = build_dataframe(args, constructor)
    if constructor in [go.Treemap, go.Sunburst, go.Icicle] and args["path"] is not None:
        args = process_dataframe_hierarchy(args)
    if constructor in [go.Pie]:
        args, trace_patch = process_dataframe_pie(args, trace_patch)
    if constructor == "timeline":
        constructor = go.Bar
        args = process_dataframe_timeline(args)

    trace_specs, grouped_mappings, sizeref, show_colorbar = infer_config(
        args, constructor, trace_patch, layout_patch
    )
    grouper = [x.grouper or one_group for x in grouped_mappings] or [one_group]
    groups, orders = get_groups_and_orders(args, grouper)

    col_labels = []
    row_labels = []
    nrows = ncols = 1
    for m in grouped_mappings:
        if m.grouper not in orders:
            m.val_map[""] = m.sequence[0]
        else:
            sorted_values = orders[m.grouper]
            if m.facet == "col":
                prefix = get_label(args, args["facet_col"]) + "="
                col_labels = [prefix + str(s) for s in sorted_values]
                ncols = len(col_labels)
            if m.facet == "row":
                prefix = get_label(args, args["facet_row"]) + "="
                row_labels = [prefix + str(s) for s in sorted_values]
                nrows = len(row_labels)
            for val in sorted_values:
                if val not in m.val_map:  # always False if it's an IdentityMap
                    m.val_map[val] = m.sequence[len(m.val_map) % len(m.sequence)]

    subplot_type = _subplot_type_for_trace_type(constructor().type)

    trace_names_by_frame = {}
    frames = OrderedDict()
    trendline_rows = []
    trace_name_labels = None
    facet_col_wrap = args.get("facet_col_wrap", 0)
    for group_name, group in groups.items():
        mapping_labels = OrderedDict()
        trace_name_labels = OrderedDict()
        frame_name = ""
        for col, val, m in zip(grouper, group_name, grouped_mappings):
            if col != one_group:
                key = get_label(args, col)
                if not isinstance(m.val_map, IdentityMap):
                    mapping_labels[key] = str(val)
                    if m.show_in_trace_name:
                        trace_name_labels[key] = str(val)
                if m.variable == "animation_frame":
                    frame_name = val
        trace_name = ", ".join(trace_name_labels.values())
        if frame_name not in trace_names_by_frame:
            trace_names_by_frame[frame_name] = set()
        trace_names = trace_names_by_frame[frame_name]

        for trace_spec in trace_specs:
            # Create the trace
            trace = trace_spec.constructor(name=trace_name)
            if trace_spec.constructor not in [
                go.Parcats,
                go.Parcoords,
                go.Choropleth,
                go.Choroplethmap,
                go.Choroplethmapbox,
                go.Densitymap,
                go.Densitymapbox,
                go.Histogram2d,
                go.Sunburst,
                go.Treemap,
                go.Icicle,
            ]:
                trace.update(
                    legendgroup=trace_name,
                    showlegend=(trace_name != "" and trace_name not in trace_names),
                )

            # Set 'offsetgroup' only in group barmode (or if no barmode is set)
            barmode = layout_patch.get("barmode")
            if trace_spec.constructor in [go.Bar, go.Box, go.Violin, go.Histogram] and (
                    barmode == "group" or barmode is None
            ):
                trace.update(alignmentgroup=True, offsetgroup=trace_name)
            trace_names.add(trace_name)

            # Init subplot row/col
            trace._subplot_row = 1
            trace._subplot_col = 1

            for i, m in enumerate(grouped_mappings):
                val = group_name[i]
                try:
                    m.updater(trace, m.val_map[val])  # covers most cases
                except ValueError:
                    # this catches some odd cases like marginals
                    if (
                            trace_spec != trace_specs[0]
                            and (
                            trace_spec.constructor in [go.Violin, go.Box]
                            and m.variable in ["symbol", "pattern", "dash"]
                    )
                            or (
                            trace_spec.constructor in [go.Histogram]
                            and m.variable in ["symbol", "dash"]
                    )
                    ):
                        pass
                    elif (
                            trace_spec != trace_specs[0]
                            and trace_spec.constructor in [go.Histogram]
                            and m.variable == "color"
                    ):
                        trace.update(marker=dict(color=m.val_map[val]))
                    elif (
                            trace_spec.constructor in [go.Choropleth, go.Choroplethmapbox]
                            and m.variable == "color"
                    ):
                        trace.update(
                            z=[1] * len(group),
                            colorscale=[m.val_map[val]] * 2,
                            showscale=False,
                            showlegend=True,
                        )
                    else:
                        raise

                # Find row for trace, handling facet_row and marginal_x
                if m.facet == "row":
                    row = m.val_map[val]
                else:
                    if (
                            args.get("marginal_x") is not None  # there is a marginal
                            and trace_spec.marginal != "x"  # and we're not it
                    ):
                        row = 2
                    else:
                        row = 1

                # Find col for trace, handling facet_col and marginal_y
                if m.facet == "col":
                    col = m.val_map[val]
                    if facet_col_wrap:  # assumes no facet_row, no marginals
                        row = 1 + ((col - 1) // facet_col_wrap)
                        col = 1 + ((col - 1) % facet_col_wrap)
                else:
                    if trace_spec.marginal == "y":
                        col = 2
                    else:
                        col = 1

                if row > 1:
                    trace._subplot_row = row

                if col > 1:
                    trace._subplot_col = col
            if (
                    trace_specs[0].constructor == go.Histogram2dContour
                    and trace_spec.constructor == go.Box
                    and trace.line.color
            ):
                trace.update(marker=dict(color=trace.line.color))

            if "ecdfmode" in args:
                base = args["x"] if args["orientation"] == "v" else args["y"]
                var = args["x"] if args["orientation"] == "h" else args["y"]
                ascending = args.get("ecdfmode", "standard") != "reversed"
                group = group.sort(by=base, descending=not ascending, nulls_last=True)
                group_sum = group.get_column(
                    var
                ).sum()  # compute here before next line mutates
                group = group.with_columns(nw.col(var).cum_sum().alias(var))
                if not ascending:
                    group = group.sort(by=base, descending=False, nulls_last=True)

                if args.get("ecdfmode", "standard") == "complementary":
                    group = group.with_columns((group_sum - nw.col(var)).alias(var))

                if args["ecdfnorm"] == "probability":
                    group = group.with_columns(nw.col(var) / group_sum)
                elif args["ecdfnorm"] == "percent":
                    group = group.with_columns((nw.col(var) / group_sum) * 100.0)

            patch, fit_results = make_trace_kwargs(
                args, trace_spec, group, mapping_labels.copy(), sizeref
            )
            trace.update(patch)
            if fit_results is not None:
                trendline_rows.append(mapping_labels.copy())
                trendline_rows[-1]["px_fit_results"] = fit_results
            if frame_name not in frames:
                frames[frame_name] = dict(data=[], name=frame_name)
            frames[frame_name]["data"].append(trace)
    frame_list = [f for f in frames.values()]
    if len(frame_list) > 1:
        frame_list = sorted(
            frame_list, key=lambda f: orders[args["animation_frame"]].index(f["name"])
        )

    if show_colorbar:
        colorvar = (
            "z"
            if constructor in [go.Histogram2d, go.Densitymap, go.Densitymapbox]
            else "color"
        )
        range_color = args["range_color"] or [None, None]

        colorscale_validator = ColorscaleValidator("colorscale", "make_figure")
        layout_patch["coloraxis1"] = dict(
            colorscale=colorscale_validator.validate_coerce(
                args["color_continuous_scale"]
            ),
            cmid=args["color_continuous_midpoint"],
            cmin=range_color[0],
            cmax=range_color[1],
            colorbar=dict(
                title_text=get_decorated_label(args, args[colorvar], colorvar)
            ),
        )

        colorscale = layout_patch["coloraxis1"]["colorscale"]
        for colorscale_ in colorscale:
            # some cases rgb(x, y, z) instead of hex is present, so
            # conversion is needed
            if 'rgb' in colorscale_[1]:
                colorscale_[1] = plotly.colors.convert_colors_to_same_type(
                    colorscale_[1],
                    colortype='tuple'
                )[0][0]
        # https://stackoverflow.com/a/46778420
        cmap = mpl.colors.LinearSegmentedColormap.from_list(
            '',
            colorscale
        )
        if args["color_continuous_midpoint"] is None:
            cmap_norm = mpl.colors.Normalize()
        else:
            cmap_norm = mpl.colors.CenteredNorm(
                vcenter=args["color_continuous_midpoint"],
            )

    for v in ["height", "width"]:
        if args[v]:
            layout_patch[v] = args[v]
    layout_patch["legend"] = dict(tracegroupgap=0)
    if trace_name_labels:
        layout_patch["legend"]["title_text"] = ", ".join(trace_name_labels)
    if args["title"]:
        layout_patch["title_text"] = args["title"]
    elif args["template"].layout.margin.t is None:
        layout_patch["margin"] = {"t": 60}
    if args["subtitle"]:
        layout_patch["title_subtitle_text"] = args["subtitle"]
    if (
            "size" in args
            and args["size"]
            and args["template"].layout.legend.itemsizing is None
    ):
        layout_patch["legend"]["itemsizing"] = "constant"

    if facet_col_wrap:
        nrows = math.ceil(ncols / facet_col_wrap)
        ncols = min(ncols, facet_col_wrap)

    if args.get("marginal_x") is not None:
        nrows += 1

    if args.get("marginal_y") is not None:
        ncols += 1

    fig, axs = init_figure(
        args, subplot_type, frame_list, nrows, ncols, col_labels, row_labels
    )

    # below line executed BEFORE plotting for sentinel to work
    configure_axes(args, constructor, axs, orders)

    # Add traces, layout and frames to figure
    axs_with_traces = set()
    bar_base = defaultdict(lambda: 0)  # https://stackoverflow.com/a/36096769
    for trace in frame_list[0]["data"] if len(frame_list) > 0 else []:
        if isinstance(trace, go.Splom):
            # Special case that is not compatible with make_subplots
            continue

        ax_index = (
            trace._subplot_row - 1,
            trace._subplot_col - 1
        )

        ax = axs[ax_index]

        marker = None
        facecolors = None
        if hasattr(trace.marker, 'symbol') and trace.marker.symbol is not None:
            marker_symbol = trace.marker.symbol
            if marker_symbol.endswith('-open'):
                marker_symbol = marker_symbol.removesuffix('-open')
                facecolors = 'None'
            elif marker_symbol.endswith('-open-dot'):
                marker_symbol = marker_symbol.removesuffix('-open-dot')
                facecolors = 'None'
            elif marker_symbol.endswith('-dot'):
                marker_symbol = marker_symbol.removesuffix('-dot')

            marker = plotly_to_mpl_marker(marker_symbol)

        if subplot_type == 'ternary':
            ax.scatter(
                trace.a,
                trace.b,
                trace.c,
                label=trace.name,
                color=trace.marker.color,
                marker=marker,
                s=trace.marker.size,
                alpha=trace.marker.opacity,
                facecolors=facecolors,
            )
        else:
            trace_x = trace.x
            if trace_x is not None:
                trace_x = trace_x.copy()
            try:
                trace_x = [datetime.datetime.strptime(date, '%Y-%m-%d') for date in trace_x]
            except (ValueError, TypeError):
                pass

            trace_y = trace.y
            if trace_y is not None:
                trace_y = trace_y.copy()
            try:
                trace_y = [datetime.datetime.strptime(date, '%Y-%m-%d') for date in trace_y]
            except (ValueError, TypeError):
                pass

            trace_x, trace_y = handle_xy_arrays(trace_x, trace_y)

            if isinstance(trace, plotly.graph_objs.Bar):
                if layout_patch['barmode'] == 'group':
                    # see https://stackoverflow.com/a/69170710
                    # for implementation
                    raise NotImplementedError
                marker_color = trace.marker.color
                if show_colorbar:
                    marker_color = cmap(cmap_norm(marker_color))

                hatch = None
                if trace.marker.pattern.shape:
                    hatch = trace.marker.pattern.shape

                def get_trace_base(x, y):
                    trace_base = np.zeros_like(y)
                    for group in np.unique(x):
                        flag = x == group
                        cum = np.cumsum(y[flag])
                        cum = np.roll(cum, 1)
                        cum[0] = 0
                        trace_base[flag] = cum + bar_base[(group, *ax_index)]
                        bar_base[(group, *ax_index)] += cum[-1] + y[flag][-1]
                    return trace_base

                if trace.orientation == 'v':
                    bars = ax.bar(
                        trace_x,
                        trace_y,
                        bottom=get_trace_base(trace_x, trace_y),
                        label=trace.name,
                        color=marker_color,
                        hatch=hatch,
                        alpha=trace.marker.opacity
                    )
                else:
                    bars = ax.barh(
                        trace_y,
                        trace_x,
                        left=get_trace_base(trace_y, trace_x),
                        label=trace.name,
                        color=marker_color,
                        hatch=hatch,
                        alpha=trace.marker.opacity
                    )
                labels = None
                if trace.text is not None:
                    labels = trace.text
                if trace.texttemplate is not None:
                    pattern = r'%{([^}]+)}'
                    matches = re.findall(pattern, trace.texttemplate)
                    labels = []
                    for trace_x_, trace_y_ in zip(trace_x, trace_y):
                        replace_map = dict(
                            x=trace_x_,
                            y=trace_y_,
                        )
                        label = trace.texttemplate
                        for variable in matches:
                            label = label.replace(
                                f'%{{{variable}}}',
                                str(replace_map.get(variable))
                            )
                        labels.append(label)
                if labels is not None:
                    ax.bar_label(bars, labels=labels, label_type='center')

            else:
                trace_modes = trace.mode.split('+')
                if 'lines' not in trace_modes:
                    marker_color = trace.marker.color
                    if show_colorbar:
                        marker_color = cmap(cmap_norm(marker_color))
                    marker_size = trace.marker.size
                    if marker_size is not None:
                        marker_size = np.array(marker_size) / trace.marker.sizeref
                        scaling_factor = 15  # Adjust this factor experimentally
                        # https://chatgpt.com/share/b34d5258-7443-4253-87f3-ce32eaa96165
                        if trace.marker.sizemode == 'diameter':
                            marker_size = (marker_size / 2) ** 2
                        elif trace.marker.sizemode == 'area':
                            marker_size = np.sqrt(marker_size)
                        else:
                            raise
                        marker_size *= scaling_factor
                    if args['size'] is not None:
                        alpha = 0.7
                    else:
                        alpha = trace.marker.opacity

                    ax.scatter(
                        trace_x,
                        trace_y,
                        label=trace.name,
                        color=marker_color,
                        marker=marker,
                        s=marker_size,
                        alpha=alpha,
                        facecolors=facecolors
                    )
                else:
                    marker_ = None
                    if 'markers' in trace_modes:
                        marker_ = marker
                    marker_color = trace.line.color
                    ax.plot(
                        trace_x,
                        trace_y,
                        label=trace.name,
                        color=trace.line.color,
                        marker=marker_,
                        alpha=trace.marker.opacity,
                        linestyle=plotly_to_mpl_linestyle(trace.line.dash),
                        drawstyle=plotly_to_mpl_drawstyle(trace.line.shape),
                        mfc=facecolors,
                    )

                if (
                        trace.error_x.array is not None or
                        trace.error_y.array is not None
                ):
                    xerr = trace.error_x.array
                    yerr = trace.error_y.array

                    if trace.error_x.arrayminus is not None:
                        xerr = [trace.error_x.arrayminus, xerr]

                    if trace.error_y.arrayminus is not None:
                        yerr = [trace.error_y.arrayminus, yerr]

                    ax.errorbar(
                        trace_x,
                        trace_y,
                        xerr=xerr,
                        yerr=yerr,
                        fmt='none',
                        ecolor=marker_color,
                        capsize=3,
                    )

                if 'text' in trace_modes:
                    for xx, yy, ss in zip(trace_x, trace_y, trace.text):
                        if xx is None or yy is None:
                            continue
                        ax.text(xx, yy, ss)

        axs_with_traces.add(ax)

    for ax in axs.flatten():
        if ax not in axs_with_traces:
            ax.axis('off')

    fig.suptitle(layout_patch.get('title_text'))
    # title_subtitle_text ignored since no support in mpl
    if layout_patch.get('width') is not None:
        fig.set_figwidth(layout_patch['width'] / PPI)
    if layout_patch.get('height') is not None:
        fig.set_figheight(layout_patch['height'] / PPI)
    if 'margin' in layout_patch:
        fig_width, fig_height = fig.get_size_inches()
        top = None
        bottom = None
        left = None
        right = None

        if 't' in layout_patch['margin']:
            top = 1 - layout_patch['margin']['t'] / (fig_height * PPI)
        if 'b' in layout_patch['margin']:
            bottom = layout_patch['margin']['b'] / (fig_height * PPI)
        if 'l' in layout_patch['margin']:
            left = layout_patch['margin']['l'] / (fig_width * PPI)
        if 'r' in layout_patch['margin']:
            right = 1 - layout_patch['margin']['r'] / (fig_width * PPI)

        fig.subplots_adjust(
            left=left,
            right=right,
            top=top,
            bottom=bottom,
        )

    # if "template" in args and args["template"] is not None:
    #     fig.update_layout(template=args["template"], overwrite=True)
    #
    if args.get("trendline") and args.get("trendline_scope", "trace") == "overall":
        trendline_spec = make_trendline_spec(args, constructor)
        trendline_trace = trendline_spec.constructor(
            name="Overall Trendline", legendgroup="Overall Trendline", showlegend=False
        )
        if "line" not in trendline_spec.trace_patch:  # no color override
            for m in grouped_mappings:
                if m.variable == "color":
                    next_color = m.sequence[len(m.val_map) % len(m.sequence)]
                    trendline_spec.trace_patch["line"] = dict(color=next_color)
        patch, fit_results = make_trace_kwargs(
            args, trendline_spec, args["data_frame"], {}, sizeref
        )
        trendline_trace.update(patch)
        # TODO for specific cases like trendline_scope 'overall':
        # fig.add_trace(
        #     trendline_trace, row="all", col="all", exclude_empty_subplots=True
        # )
        # fig.update_traces(selector=-1, showlegend=True)
        # if fit_results is not None:
        #     trendline_rows.append(dict(px_fit_results=fit_results))

    if show_colorbar:
        mappable = mpl.cm.ScalarMappable(cmap=cmap, norm=cmap_norm)
        mappable.set_clim(range_color)
        fig.colorbar(
            mappable,
            ax=axs,
            label=layout_patch["coloraxis1"]['colorbar']['title_text']
        )
    fig_legend(fig, legend_title=layout_patch.get('legend', {}).get('title_text'))
    return fig
