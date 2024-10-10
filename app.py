from dash import Dash, Input, Output, dcc, html, State, no_update, callback_context
import dash_mantine_components as dmc
from dash_snap_grid import Grid
from flowfunc import Flowfunc
from flowfunc.config import Config
from flowfunc.jobrunner import JobRunner
from flowfunc.models import OutNode
from flowfunc.types import color
from PIL import Image, ImageDraw
import base64
from io import BytesIO
import requests

app = Dash(__name__)

SCALE_FACTOR = 4

def hex_to_rgb(hex_color: str) -> tuple:
    """
    Convert a hex color string to an RGB tuple.

    :param hex_color: A string representing a hex color (e.g., "#RRGGBB" or "RRGGBB").
    :return: A tuple (R, G, B) representing the RGB color.
    """
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def create_canvas(width: int, height: int, background_color: color) -> Image.Image:
    """Create an empty canvas with the given height and width."""
    return Image.new(
        "RGBA", (width * SCALE_FACTOR, height * SCALE_FACTOR), background_color
    )


def preview_image(image: Image.Image) -> html.Img:
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

def circle(radius: int, color: color, transparency: int) -> Image.Image:
    """Draw a circle on the image with the given opacity."""
    radius = radius * SCALE_FACTOR

    image = Image.new("RGBA", (2 * radius, 2 * radius), (255, 255, 255, 0))

    draw = ImageDraw.Draw(image)
    opacity = int(255 - 255 * (transparency / 100))
    color_with_opacity = (*hex_to_rgb(color)[:3], opacity)
    draw.ellipse((0, 0, 2 * radius, 2 * radius), fill=color_with_opacity)
    return image

def shape_from_url(url: str, height: int, width: int) -> Image.Image:
    """Create an image from a URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    return image.resize((width * SCALE_FACTOR, height * SCALE_FACTOR))


def change_color(image: Image.Image, color: color) -> Image.Image:
    """Change the color of the image."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    data = image.getdata()
    new_data = []
    for item in data:
        # if the pixel is transparent, keep it transparent
        if item[3] == 0:
            new_data.append(item)
        else:
            new_data.append(hex_to_rgb(color) + (item[3],))
    image.putdata(new_data)
    return image

def change_transparency(image: Image.Image, transparency: int) -> Image.Image:
    """Change the transparency of the image."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    data = image.getdata()
    new_data = []
    opacity = int(255 - 255 * (transparency / 100))
    for item in data:
        new_data.append((*item[:3], int(item[3] * opacity)))
    image.putdata(new_data)
    return image


def rectangle(width: int, height: int, color: color, transparency: int) -> Image.Image:
    """Draw a rectangle on the image with the given opacity."""
    width = width * SCALE_FACTOR
    height = height * SCALE_FACTOR

    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))

    draw = ImageDraw.Draw(image)
    opacity = int(255 - 255 * (transparency / 100))
    color_with_opacity = (*hex_to_rgb(color)[:3], opacity)
    draw.rectangle((0, 0, width, height), fill=color_with_opacity)
    return image


def rectangular_pattern(
    image: Image.Image, count_x: int, count_y: int, step_x: int, step_y: int
) -> Image.Image:
    """Repeat the image in a rectangular pattern, overlaying on top of existing pixels."""
    step_x = step_x * SCALE_FACTOR
    step_y = step_y * SCALE_FACTOR
    width, height = image.size
    new_width = count_x * step_x
    new_height = count_y * step_y
    if step_x < width:
        new_width += width - step_x
    if step_y < height:
        new_height += height - step_y
    new_image = Image.new("RGBA", (new_width, new_height), (255, 255, 255, 0))
    for x in range(0, count_x):
        for y in range(0, count_y):
            new_image.alpha_composite(image, (x * step_x, y * step_y))
    return new_image


def overlay_images(
    base_image: Image.Image,
    overlay_image: Image.Image,
    offset_x: int,
    offset_y: int,
    transparency: int,
) -> Image.Image:
    """
    Overlay an image on top of another image with the given position and transparency.
    """
    # Ensure the overlay image has an alpha channel
    position = (offset_x * SCALE_FACTOR, offset_y * SCALE_FACTOR)
    if overlay_image.mode != "RGBA":
        overlay_image = overlay_image.convert("RGBA")

    # Apply transparency to the overlay image
    if transparency < 255:
        overlay_image = overlay_image.copy()
        alpha = overlay_image.split()[3]
        alpha = Image.eval(alpha, lambda a: int(a * (transparency / 255)))
        overlay_image.putalpha(alpha)

    # Calculate the region of the overlay image that fits within the base image
    base_width, base_height = base_image.size
    overlay_width, overlay_height = overlay_image.size
    x, y = position

    # Determine the region of the overlay image that is within the base image bounds
    if x < 0:
        overlay_image = overlay_image.crop((-x, 0, overlay_width, overlay_height))
        x = 0
    if y < 0:
        overlay_image = overlay_image.crop((0, -y, overlay_width, overlay_height))
        y = 0
    if x + overlay_width > base_width:
        overlay_image = overlay_image.crop((0, 0, base_width - x, overlay_height))
    if y + overlay_height > base_height:
        overlay_image = overlay_image.crop((0, 0, overlay_width, base_height - y))

    # Create a new image with the same size as the base image and an alpha channel
    combined_image = base_image.convert("RGBA")
    combined_image.paste(overlay_image, (x, y), overlay_image)

    return combined_image

def rotate(image: Image.Image, angle: int) -> Image.Image:
    """Rotate the image by the given angle."""
    return image.rotate(angle, expand=True)


config = Config.from_function_list(
    [
        create_canvas,
        preview_image,
        circle,
        rectangular_pattern,
        overlay_images,
        rectangle,
        rotate,
        shape_from_url,
        change_color,
        change_transparency,
    ]
)
job_runner = JobRunner(config)


app.layout = dmc.MantineProvider(
    html.Div(
        [
            Flowfunc(
                id="flowfunc",
                config=config.dict(),
            ),
            html.Div(
                id="buttons",
                children=[
                    dmc.ButtonGroup(
                        [
                            dmc.Button("Run", id="run-button"),
                            dmc.Button("Save", id="save-button"),
                            dcc.Store(id="save-store", storage_type="local"),
                            dmc.Button("Restore", id="restore-button"),
                            dmc.Button("Clear", id="clear-button"),
                        ]
                    )
                ],
            ),
            html.Div(
                Grid(
                    id="grid",
                    cols=24,
                    rowHeight=50,
                    layout=[
                        {"i": "output", "x": 22, "y": 0, "w": 2, "h": 2},
                    ],
                    resizeHandles=["nw", "ne", "sw", "se"],
                    children=[
                        html.Div(
                            id="output",
                        ),
                    ],
                ),
                id="grid-container",
            ),
        ],
        id="app",
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
    if not outnodes:
        return no_update, [{"id": node["id"], "status": "error"} for node in nodes]
    nodes_status = {}
    children = []
    for id, outnode in outnodes.items():
        nodes_status[id] = outnode.status
        if outnode.status == "failed":
            print(outnode.error)
        if outnode.type == "__main__.preview_image":
            children.append(outnode.result)
    return children, nodes_status

@app.callback(
    Output("save-store", "data"),
    Input("save-button", "n_clicks"),
    State("flowfunc", "nodes"),
)
def save_image(n_clicks, nodes):
    if n_clicks is None or not nodes:
        return no_update
    return nodes


@app.callback(
    Output("flowfunc", "nodes"),
    Output("flowfunc", "editor_status"),
    Input("restore-button", "n_clicks"),
    Input("clear-button", "n_clicks"),
    State("save-store", "data"),
    State("flowfunc", "nodes"),
)
def restore_image(n_clicks_restore, n_clicks_clear, store_data, nodes):
    if not callback_context.triggered:
        return nodes, "server"
    control = callback_context.triggered_id
    if control == "restore-button":
        if store_data:
            return store_data, "server"
        return no_update, no_update
    elif control == "clear-button":
        return {}, "server"
    return nodes, "server"


if __name__ == "__main__":
    app.run_server(debug=True)
