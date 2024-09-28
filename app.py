from dash import Dash, Input, Output, dcc, html, State, no_update
from dash.development.base_component import Component
import dash_mantine_components as dmc
from dash_snap_grid import Grid
from flowfunc import Flowfunc
from flowfunc.config import Config
from flowfunc.jobrunner import JobRunner
from flowfunc.models import OutNode
from flowfunc.types import color
from PIL import Image
import base64
from io import BytesIO

app = Dash(__name__)

SCALE_FACTOR = 4


def create_canvas(width: int, height: int, background_color: color) -> Image.Image:
    """Create an empty canvas with the given height and width."""
    return Image.new(
        "RGB", (width * SCALE_FACTOR, height * SCALE_FACTOR), background_color
    )


def save_image(image: Image.Image) -> html.Img:
    """Display image"""
    image = image.resize(
        (image.width // SCALE_FACTOR, image.height // SCALE_FACTOR),
        Image.Resampling.LANCZOS,
    )
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return html.Img(
        src=f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode("utf-8")}",
        style={"max-width": "100%", "max-height": "100%"},
    )


config = Config.from_function_list([create_canvas, save_image])
job_runner = JobRunner(config)


app.layout = dmc.MantineProvider(
    html.Div(
        [
            Flowfunc(
                id="flowfunc",
                config=config.dict(),
                style={"width": "100%", "height": "100vh"},
            ),
            html.Div(
                id="buttons",
                children=[
                    dmc.Button("Run", id="run-button"),
                ],
                style={"position": "absolute", "top": "10px", "left": "10px"},
            ),
            html.Div(
                Grid(
                    id="grid",
                    cols=24,
                    rowHeight=50,
                    layout=[
                        {"i": "output", "x": 10, "y": 10, "w": 2, "h": 2},
                    ],
                    children=[
                        html.Div(
                            id="output",
                        ),
                    ],
                ),
                id="grid-container",
            ),
        ],
        style={"width": "100%", "height": "100vh"},
    )
)


@app.callback(
    Output("output", "children"),
    Output("flowfunc", "nodes_status"),
    Input("run-button", "n_clicks"),
    State("flowfunc", "nodes"),
)
def run_job(n_clicks, nodes):
    if n_clicks is None or not nodes:
        return no_update, no_update
    outnodes = job_runner.run(nodes)
    print(outnodes)
    if not outnodes:
        return no_update, [{"id": node["id"], "status": "error"} for node in nodes]
    nodes_status = {}
    children = []
    for id, outnode in outnodes.items():
        nodes_status[id] = outnode.status
        if outnode.type == "__main__.save_image":
            children.append(outnode.result)
    return children, nodes_status


if __name__ == "__main__":
    app.run_server(debug=True)
