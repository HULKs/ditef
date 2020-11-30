import textwrap
import json

def show_convolutional_layer(individual,
                             index,
                             x_index,
                             filters,
                             layer,
                             is_pooling,
                             image_height,
                             spacer,
                             font_size,
                             free_lines_below,
                             enlarge_factor,
                             original_input_size,
                             with_text):
    result = ''
    input_size = int(individual.size_after_convolution_layers(up_to_index = index-1)) #TODO: Stride is wrong
    if is_pooling:
        input_size = int(individual.size_after_convolution_layers(up_to_index = index))

    result += f'''<text x="{spacer + (x_index * ((original_input_size * enlarge_factor) + (2*spacer))) + ((original_input_size - input_size) * enlarge_factor / 2)}"
                        y="{image_height - spacer - ((font_size + spacer) * (free_lines_below - 1))}"
                        fill="black"
                        font-size="{font_size}px">{input_size}x{input_size}x{filters}</text>'''
#    tooltip = json.dumps(layer, indent=0, separators=(',&#10;', ': '))[1:-2].replace('\n', '').replace('"', '')
    i_list = list(range(filters))
    i_list.reverse()

    if is_pooling and with_text:
        result += f'''<text x="{spacer + ((x_index - 0.5) * ((original_input_size * enlarge_factor) + (2*spacer))) + ((original_input_size - input_size) * enlarge_factor / 2)}"
                        y="{image_height - spacer - ((font_size + spacer) * (free_lines_below - 3))}"
                        fill="black"
                        font-size="{font_size}px">Pooling</text>'''
    elif with_text:
        result += f'''<text x="{spacer + ((x_index - 0.5) * ((original_input_size * enlarge_factor) + (2*spacer))) + ((original_input_size - input_size) * enlarge_factor / 2)}"
                        y="{image_height - spacer - ((font_size + spacer) * (free_lines_below - 3))}"
                        fill="black"
                        font-size="{font_size}px">{layer['type']}</text>'''

    for i in i_list:
        x = spacer + (x_index * ((original_input_size * enlarge_factor) + (2*spacer))) + (i*5) + ((original_input_size - input_size) * enlarge_factor / 2)
        y = image_height - (input_size * enlarge_factor) - ((font_size + spacer) * free_lines_below) - (i*5) - ((original_input_size - input_size) * enlarge_factor / 2)
        width = enlarge_factor * individual.size_after_convolution_layers(up_to_index = index-1)
        height = enlarge_factor * individual.size_after_convolution_layers(up_to_index = index-1)
        if is_pooling:
            width = enlarge_factor * individual.size_after_convolution_layers(up_to_index = index)
            height = enlarge_factor * individual.size_after_convolution_layers(up_to_index = index)
        result += f'''<rect x="{x}"
                            y="{y}"
                            width="{width}"
                            height="{height}"
                            stroke="black" stroke-width="2" fill="white"></rect>'''
    return result


def show_individual(individual_id, individual, parents_list, children_list):
    image_width = 1880
    image_height = 512
    spacer = 8
    font_size = 20
    free_lines_below = 5
    enlarge_factor = 5
    original_input_size = 32
    svg_convolutions = ''
    svg_convolutions += f'''<rect x="1" y="1"
                width="{image_width - 2}"
                height="{image_height - 2}"
                stroke="black" stroke-width="2" fill="white" />'''
    svg_dense = ""
    svg_output = ""
    svg_convolutions += show_convolutional_layer(individual,
                                                 0,
                                                 0,
                                                 individual.configuration['input_channels'],
                                                 individual.genome['convolution_layers'][0],
                                                 False,
                                                 image_height,
                                                 spacer,
                                                 font_size,
                                                 free_lines_below,
                                                 enlarge_factor,
                                                 original_input_size,
                                                 False)
    index_offset = 1
    for index, layer in enumerate(individual.genome['convolution_layers']):
        svg_convolutions += show_convolutional_layer(individual,
                                                     index,
                                                     index + index_offset,
                                                     layer['filters'],
                                                     layer,
                                                     False,
                                                     image_height,
                                                     spacer,
                                                     font_size,
                                                     free_lines_below,
                                                     enlarge_factor,
                                                     original_input_size,
                                                     True)

        if layer["pooling_type"]:
            index_offset += 1
            svg_convolutions += show_convolutional_layer(individual,
                                                         index,
                                                         index + index_offset,
                                                         layer['filters'],
                                                         layer,
                                                         True,
                                                         image_height,
                                                         spacer,
                                                         font_size,
                                                         free_lines_below,
                                                         enlarge_factor,
                                                         original_input_size,
                                                         True)

    return textwrap.dedent(f'''
        <!DOCTYPE html>
        <html>
            <head>
                <title>{individual.creation_type} individual {individual_id}</title>
            </head>
            <body>
                <svg width="{image_width}" height="{image_height}">
                {svg_convolutions}
                {svg_dense}
                {svg_output}
                </svg>
                <h1>Genetic Individual (Positioner) - DEBUG</h1>
                <h2>ID</h2>
                <p>{individual_id}</p>
                <h2>Genome</h2>
                <p><pre>{json.dumps(individual.genome, indent=4)}</pre></p>
                <h2>Configuration</h2>
                <p><pre>{json.dumps(individual.configuration, indent=4)}</pre></p>
                <h2>Fitness</h2>
                <p>{individual.fitness()}</p>
                <h2>Evaluation result</h2>
                <p><pre>{json.dumps(individual.evaluation_result, indent=4)}</pre></p>
                <h2>Computational costs</h2>
                <p>{individual.computational_cost} multiplied by factor
                {individual.configuration['computational_cost_factor']}</p>
                <h2>Creation Type</h2>
                {individual.creation_type}
                <h2>Parents</h2>
                {parents_list}
                <h2>Children</h2>
                {children_list}
            </body>
        </html>
    ''')
