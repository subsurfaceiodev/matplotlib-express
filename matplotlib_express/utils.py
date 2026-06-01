import matplotlib.pyplot as plt


def fig_legend(
        fig: plt.Figure,
        legend_title: str | None = None,
        fontsize: float | str = 'small'
):
    # https://stackoverflow.com/a/57484812/10315746
    lines_labels = [ax.get_legend_handles_labels() for ax in fig.axes]
    lines, labels = [sum(lol, []) for lol in zip(*lines_labels)]
    by_label = dict(zip(labels, lines))
    if by_label:
        fig.legend(
            by_label.values(),
            by_label.keys(),
            title=legend_title,
            loc='upper right',
            bbox_to_anchor=(1.0, 0.9),
            fontsize=fontsize,
            title_fontsize=fontsize,
        )
