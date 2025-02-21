import math

from pathlib import Path

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
import svgwrite


def get_polygon_inside_circle_corner_positions(
    num_sides: int,
    circle_diameter: float,
) -> list[float, float]:
    positions = []
    radius = circle_diameter / 2
    angle_increment = 2 * math.pi / num_sides

    for i in range(num_sides):
        angle = i * angle_increment
        x = radius + radius * math.cos(angle)
        y = radius + radius * math.sin(angle)
        positions.append((x, y))

    return positions


def get_polygon_inside_circle_side_length(
    num_sides: int,
    circle_diameter: float,
) -> float:
    radius = circle_diameter / 2
    side_length = 2 * radius * math.sin(math.pi / num_sides)
    return side_length


def get_marker_positions_and_size(
    disk_diameter_mm: int,
    number_of_marker: int,
    distance_between_markers_mm: int = 2,
    marker_circle_diameter_reduction_ratio: float = 2,
) -> tuple[list[float, float], float]:
    # First iteration to find polygon the fits exactly on the disk radius
    positions = get_polygon_inside_circle_corner_positions(
        number_of_marker, disk_diameter_mm
    )
    side_length = get_polygon_inside_circle_side_length(
        number_of_marker, disk_diameter_mm
    )
    marker_radius_mm = side_length / 2 - distance_between_markers_mm
    if marker_radius_mm < 0:
        raise ValueError(
            "Markers are too close to each other, reduce distance_between_markers_mm!"
        )
    marker_diameter_mm = 2 * marker_radius_mm
    marker_circle_diameter_mm = (
        disk_diameter_mm - marker_circle_diameter_reduction_ratio * marker_diameter_mm
    )

    # Second iteration to find polygon the fits well inside the disk radius
    positions = get_polygon_inside_circle_corner_positions(
        number_of_marker, marker_circle_diameter_mm
    )
    side_length = get_polygon_inside_circle_side_length(
        number_of_marker, marker_circle_diameter_mm
    )
    marker_radius_mm = side_length / 2 - distance_between_markers_mm
    if marker_radius_mm < 0:
        raise ValueError(
            "Markers are too close to each other, reduce distance_between_markers_mm!"
        )

    return positions, marker_radius_mm


def main(
    disk_diameter_mm: int = 120,
    marker_radius_mm: int = 10,
    disk_border_thickness_mm: int = 2,
    out_filename: str = "target_disk.pdf",
    marker_ring_count: int = 3,
    add_id: bool = True,
    add_cross: bool = True,
    cross_ratio: float = 0.7,
):
    out_path = Path(__file__).parent.joinpath(out_filename).resolve()
    width, height = LETTER
    cx, cy = width / 2, height / 2  # Center of the page
    disk_diameter_mm = disk_diameter_mm * mm
    inner_disk_diameter_mm = disk_diameter_mm - 2 * disk_border_thickness_mm

    if marker_ring_count == 3:
        input_file = "cctag3.txt"
    elif marker_ring_count == 4:
        input_file = "cctag4.txt"
    else:
        raise ValueError("marker_ring_count must be 3 or 4")
    with open(input_file) as f:
        number_of_marker = len([_ for _ in f])

    markers_positions, marker_radius_mm = get_marker_positions_and_size(
        disk_diameter_mm=inner_disk_diameter_mm,
        number_of_marker=number_of_marker,
    )
    max_x = max(x for x, y in markers_positions)
    max_y = max(y for x, y in markers_positions)
    markers_positions = [
        (cx + (x - max_x / 2), cy + (y - max_y / 2)) for x, y in markers_positions
    ]  # Shift to the center of the

    dwg = svgwrite.Drawing(
        out_path.with_suffix(".svg"), profile="tiny", size=(width, height)
    )
    # Create disk outer trace
    dwg.add(dwg.circle(center=(cx, cy), r=disk_diameter_mm / 2, fill="black"))
    dwg.add(
        dwg.circle(
            center=(cx, cy),
            r=(inner_disk_diameter_mm) / 2,
            fill="white",
        )
    )
    # Normalized size of the marker radius
    marker_scale = marker_radius_mm / 100

    # font size for the id
    font_size = int(0.5 * marker_radius_mm)

    with open(input_file) as f:
        for ind, line in enumerate(f):
            # center of the marker
            marker_center = markers_positions[ind]

            # print the id of the marker
            if add_id:
                dwg.add(
                    dwg.text(
                        text=str(ind + 1),
                        insert=(
                            marker_center[0] - marker_radius_mm,
                            marker_center[1] - marker_radius_mm,
                        ),
                        font_size=font_size,
                    )
                )

            # print the outer circle as black
            dwg.add(dwg.circle(center=marker_center, r=marker_radius_mm, fill="black"))

            fill_color = "white"
            count = 0
            # each value of the line is the radius of the circle to draw
            # the values are given for a marker of radius 100 (so scale it accordingly to the given size)
            for marker_inner_circle_ratio in line.split():
                marker_inner_circle_radius = marker_scale * int(
                    marker_inner_circle_ratio
                )
                dwg.add(
                    dwg.circle(
                        center=marker_center,
                        r=marker_inner_circle_radius,
                        fill=fill_color,
                    )
                )
                if fill_color == "white":
                    fill_color = "black"
                else:
                    fill_color = "white"
                count = count + 1

            # sanity check
            if marker_ring_count == 3:
                assert count == 5
            else:
                assert count == 7

            if add_cross:
                # print a small cross in the center
                dwg.add(
                    dwg.line(
                        start=(
                            marker_center[0] - marker_inner_circle_radius * cross_ratio,
                            marker_center[1],
                        ),
                        end=(
                            marker_center[0] + marker_inner_circle_radius * cross_ratio,
                            marker_center[1],
                        ),
                        stroke="gray",
                    )
                )
                dwg.add(
                    dwg.line(
                        start=(
                            marker_center[0],
                            marker_center[1] - marker_inner_circle_radius * cross_ratio,
                        ),
                        end=(
                            marker_center[0],
                            marker_center[1] + marker_inner_circle_radius * cross_ratio,
                        ),
                        stroke="gray",
                    )
                )

    dwg.save(pretty=True)
    drawing = svg2rlg(out_path.with_suffix(".svg"))
    renderPDF.drawToFile(drawing, str(out_path))
    print(f"Target disk saved!")


if __name__ == "__main__":
    main()
