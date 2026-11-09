"""Line charts whose hover tooltip shows the date and time (UTC) of each reading."""
import altair as alt


def time_series_chart(frame, columns, colors=None, height=300):
    """Plot frame["Date"] against one or more numeric columns.

    Hovering shows the reading's date and time in UTC, which series it is, and its value.
    frame["Date"] must be timezone-aware UTC (as readings_to_frame / history_frame return).
    """
    data = frame.melt(id_vars="Date", value_vars=columns,
                      var_name="Reading", value_name="Value").dropna(subset=["Value"])
    data["Reading"] = data["Reading"].str.capitalize()
    labels = [column.capitalize() for column in columns]
    data["Time (UTC)"] = data["Date"].dt.strftime("%Y-%m-%d %H:%M UTC")
    data["Date"] = data["Date"].dt.tz_convert(None)  # plot UTC as-is, not browser local time

    color_scale = alt.Scale(domain=labels, range=colors) if colors else alt.Scale(domain=labels)
    hover = alt.selection_point(fields=["Date"], nearest=True, on="pointerover",
                                empty=False, clear="pointerout")
    base = alt.Chart(data).encode(
        x=alt.X("Date:T", title="Date (UTC)", scale=alt.Scale(type="utc"),
                axis=alt.Axis(format="%b %d %H:%M")),
        y=alt.Y("Value:Q", title=None, scale=alt.Scale(zero=False)),
        color=alt.Color("Reading:N", title=None, scale=color_scale,
                        legend=alt.Legend(orient="bottom") if len(columns) > 1 else None),
    )
    lines = base.mark_line()
    points = base.mark_circle(size=70).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("Time (UTC):N"), alt.Tooltip("Reading:N"),
                 alt.Tooltip("Value:Q", format="g")],
    ).add_params(hover)
    return (lines + points).properties(height=height)
