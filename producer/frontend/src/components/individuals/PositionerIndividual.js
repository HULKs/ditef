import React, { useState, useEffect, useCallback } from "react";
import {
  Container,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@material-ui/core";
import {
  makeStyles,
} from "@material-ui/core/styles";
import {
  Link,
} from "react-router-dom";

import useWebSocket from "../../hooks/useWebSocket";

const useStyles = makeStyles(theme => ({
  headingSpacing: {
    marginTop: theme.spacing(2),
    marginBottom: theme.spacing(1),
  },
  genomePaper: {
    paddingTop: theme.spacing(0.5),
    paddingBottom: theme.spacing(0.5),
    paddingLeft: theme.spacing(2),
    paddingRight: theme.spacing(2),
  },
  genome: {
    //fontSize: theme.spacing(5),
  },
  fitnessPaper: {
    paddingTop: theme.spacing(0.5),
    paddingBottom: theme.spacing(0.5),
    paddingLeft: theme.spacing(2),
    paddingRight: theme.spacing(2),
  },
  fitness: {
    fontSize: theme.spacing(5),
  },
  noWrap: {
    whiteSpace: "nowrap",
  },
  noParentsOrChildren: {
    textAlign: "center",
    fontStyle: "italic",
  },
}));

function createConvLayerVisualization(x_index, key, filters, image_height, spacer, font_size, free_lines_below, enlarge_factor, original_input_size, input_size, strokeWidth, stackOffset, type, kernel_size) {
  var svgCoponents = [];

  for (var i = filters-1; i>=0; i--) {
    var x = (x_index * ((original_input_size * enlarge_factor) + (2*spacer))) + (i*stackOffset/2) + ((original_input_size - input_size) * enlarge_factor / 2);
    var  y = image_height - (input_size * enlarge_factor) - ((font_size + spacer) * free_lines_below) - (i*stackOffset) - ((original_input_size - input_size) * enlarge_factor / 2);
    var width = enlarge_factor * input_size;
    var height = enlarge_factor * input_size;

    svgCoponents.push(
      <rect
        x={x+strokeWidth}
        y={y}
        width={width}
        height={height}
        strokeWidth={strokeWidth}
        stroke="black"
        fill="white"
        key={key.toString() + "_" + i.toString()} />);

  }
  x = (x_index * ((original_input_size * enlarge_factor) + (2*spacer))) + ((original_input_size - input_size) * enlarge_factor / 2);
  y = image_height - spacer - ((font_size + spacer) * (free_lines_below - 1));

  svgCoponents.push(
    <text x={x+strokeWidth}
      y={y}
      fill="black"
      fontSize={font_size.toString() +"px"}
      key={key.toString() + "_text1"}>{input_size}x{input_size}x{filters}</text>);

  x = ((x_index - 0.5) * ((original_input_size * enlarge_factor) + (2*spacer))) + ((original_input_size - input_size) * enlarge_factor / 2);
  y = image_height - spacer - ((font_size + spacer) * (free_lines_below - 3));

  svgCoponents.push(
    <text x={x+strokeWidth}
      y={y}
      fill="black"
      fontSize={font_size.toString() +"px"}
      key={key.toString() + "_text2"}>{type}</text>);

  y = image_height - spacer - ((font_size + spacer) * (free_lines_below - 4));

  svgCoponents.push(
    <text x={x+strokeWidth}
      y={y}
      fill="black"
      fontSize={font_size.toString() +"px"}
      key={key.toString() + "_text3"}>{kernel_size}</text>);

  return svgCoponents;
}

function createDenseLayerVisualization(x_index, key, image_height, spacer, font_size, free_lines_below, enlarge_factor, original_input_size, strokeWidth, neurons, type, activation) {
  var svgCoponents = [];
  var layer_size = 2 * Math.log(neurons);
  var x = (x_index * ((original_input_size * enlarge_factor) + (2*spacer)));
  var  y = image_height - (layer_size * enlarge_factor) - ((font_size + spacer) * free_lines_below) - ((original_input_size - layer_size) * enlarge_factor / 2);
  var width = enlarge_factor * 2;
  var height = enlarge_factor * layer_size;

  svgCoponents.push(
    <rect
      x={x+strokeWidth}
      y={y}
      width={width}
      height={height}
      strokeWidth={strokeWidth}
      stroke="black"
      fill="white"
      key={key} />);

  x = (x_index * ((original_input_size * enlarge_factor) + (2*spacer)));
  y = image_height - spacer - ((font_size + spacer) * (free_lines_below - 1));

  svgCoponents.push(
    <text x={x+strokeWidth}
      y={y}
      fill="black"
      fontSize={font_size.toString() +"px"}
      key={key.toString() + "_text1"}>{neurons}</text>);

  y = image_height - spacer - ((font_size + spacer) * (free_lines_below - 3));
  svgCoponents.push(
    <text x={x+strokeWidth}
      y={y}
      fill="black"
      fontSize={font_size.toString() +"px"}
      key={key.toString() + "_text2"}>{type}</text>);

  y = image_height - spacer - ((font_size + spacer) * (free_lines_below - 4));
  svgCoponents.push(
    <text x={x+strokeWidth}
      y={y}
      fill="black"
      fontSize={font_size.toString() +"px"}
      key={key.toString() + "_text3"}>{activation}</text>);

  return svgCoponents;
}

function createArchitectureVisualization(genome, configuration) {
  var svgCoponents = [];
  var componentKey = 0;
  const image_height = 256;
  const spacer = 6;
  const font_size = 12;
  const free_lines_below = 6;
  const enlarge_factor = 3;
  const original_input_size = 32;
  const stackOffset = 3;
  const strokeWidth = 1;
  var index_offset = 0;
  var input_size = original_input_size;

  // input layer
  svgCoponents = svgCoponents.concat(
    createConvLayerVisualization(index_offset, componentKey++, configuration.input_channels, image_height, spacer, font_size, free_lines_below, enlarge_factor, original_input_size, input_size, strokeWidth, stackOffset, "", "")
  );

  // convolutional layers
  for (var i = 0; i < genome.convolution_layers.length; i++) {
    index_offset += 1;
    input_size = input_size / genome.convolution_layers[i].stride;
    svgCoponents = svgCoponents.concat(
      createConvLayerVisualization(index_offset, componentKey++, genome.convolution_layers[i].filters, image_height, spacer, font_size, free_lines_below, enlarge_factor, original_input_size, input_size, strokeWidth, stackOffset, genome.convolution_layers[i].type, "kernel: " + genome.convolution_layers[i].kernel_size.toString()+"x"+genome.convolution_layers[i].kernel_size.toString())
    );

    if (genome.convolution_layers[i].pooling_size > 1) {
      index_offset += 1;
      input_size = input_size / genome.convolution_layers[i].pooling_size;
      svgCoponents = svgCoponents.concat(
        createConvLayerVisualization(index_offset, componentKey++, genome.convolution_layers[i].filters, image_height, spacer, font_size, free_lines_below, enlarge_factor, original_input_size, input_size, strokeWidth, stackOffset,  genome.convolution_layers[i].pooling_type+" pool", "kernel: " + genome.convolution_layers[i].pooling_size.toString()+"x"+genome.convolution_layers[i].pooling_size.toString())
      );
    }
  }

  // Flatten layer
  var flat_neurons = input_size * input_size * genome.convolution_layers[genome.convolution_layers.length-1].filters;

  index_offset += 1;
  svgCoponents = svgCoponents.concat(
    createDenseLayerVisualization(index_offset, componentKey++, image_height, spacer, font_size, free_lines_below, enlarge_factor, original_input_size, strokeWidth, flat_neurons, "Flatten", "")
  );

  // Dense layers

  for (var j = 0; j < genome.dense_layers.length; j++){
    index_offset += 0.5;
    svgCoponents = svgCoponents.concat(
      createDenseLayerVisualization(index_offset, componentKey++, image_height, spacer, font_size, free_lines_below, enlarge_factor, original_input_size, strokeWidth, genome.dense_layers[j].units, "Dense", genome.dense_layers[j].activation_function)
    );
  }

  // Output layer
  index_offset += 0.5;
  svgCoponents = svgCoponents.concat(
    createDenseLayerVisualization(index_offset, componentKey++, image_height, spacer, font_size, free_lines_below, enlarge_factor, original_input_size, strokeWidth, configuration.final_layer_neurons, "Output", genome.final_layer_activation_function)
  );

  return svgCoponents;
}

export default function PositionerIndividual({ url, onConnectedChange }) {
  const classes = useStyles();
  const [genome, setGenome] = useState();
  const [configuration, setConfiguration] = useState();
  const [computationalCost, setComputationalCost] = useState();
  const [evaluationResult, setEvaluationResult] = useState();
  const [fitness, setFitness] = useState();
  const [creationType, setCreationType] = useState();
  const [genealogyParents, setGenealogyParents] = useState();
  const [genealogyChildren, setGeneaglogyChildren] = useState();
  const onWebSocketMessage = useCallback((type, payload) => {
    switch (type) {
      case "genome": {
        setGenome(payload);
        break;
      }
      case "configuration": {
        setConfiguration(payload);
        break;
      }
      case "computational_cost": {
        setComputationalCost(payload);
        break;
      }
      case "evaluation_result": {
        setEvaluationResult(payload);
        break;
      }
      case "fitness": {
        setFitness(payload);
        break;
      }
      case "creation_type": {
        setCreationType(payload);
        break;
      }
      case "genealogy_parents": {
        setGenealogyParents(payload);
        break;
      }
      case "genealogy_children": {
        setGeneaglogyChildren(payload);
        break;
      }
      default: {
        console.warn(`Message type ${type} not implemented.`);
        break;
      }
    }
  }, []);
  const [connected, error,] = useWebSocket(
    true,
    `ws://localhost:8081${url}`,
    onWebSocketMessage,
  );

  useEffect(() => {
    onConnectedChange(connected);
  }, [onConnectedChange, connected]);

  if (error) {
    return <>Error: {JSON.stringify(error)}</>;
  }

  if (!connected) {
    return <Typography>Loading...</Typography>;
  }

  return <>
    <Container>
      <Typography variant="h5" className={classes.headingSpacing}>Positioner Genome</Typography>
      <Paper elevation={3} className={classes.genomePaper}>
        <svg width="100%" height="256">
          <rect x="0" y="0"
            width="100%"
            height="256"
            strokeWidth="0"
            fill="white" />
          {genome && configuration && createArchitectureVisualization(genome, configuration)}
        </svg>
        {genome && <pre>{JSON.stringify(genome,null,2)}</pre>}
        {configuration && <pre>{JSON.stringify(configuration,null,2)}</pre>}
        {computationalCost && <pre>{JSON.stringify(computationalCost,null,2)}</pre>}
        {evaluationResult && <pre>{JSON.stringify(evaluationResult,null,2)}</pre>}
      </Paper>
    </Container>
    <Container>
      <Typography variant="h5" className={classes.headingSpacing}>Fitness</Typography>
      <Paper elevation={3} className={classes.fitnessPaper}>
        <Typography className={classes.fitness}>
          {fitness}
          {!fitness && "waiting for evaluation..."}
        </Typography>
      </Paper>
    </Container>
    <Container>
      <Grid container spacing={2}>
        <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
          <Typography variant="h5" className={classes.headingSpacing}>&quot;{creationType}&quot; Parents</Typography>
          <TableContainer component={({ ...props }) => <Paper elevation={3} {...props} />}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell className={classes.noWrap}>Individual</TableCell>
                  <TableCell className={classes.noWrap}>Fitness</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {genealogyParents && Object.entries(genealogyParents).sort(([, parentA], [, parentB]) => parentB.fitness - parentA.fitness).map(([parentId, parent]) =>
                  <TableRow key={parentId}>
                    <TableCell className={classes.noWrap}>
                      <Link to={`/individual/${parentId}?type=ditef_producer_genetic_individual_positioner&url=${encodeURIComponent(parent.url)}`}>{parentId}</Link>
                    </TableCell>
                    <TableCell className={classes.noWrap}>{parent.fitness ? parent.fitness : "N/A"}</TableCell>
                  </TableRow>
                )}
                {(!genealogyParents || Object.keys(genealogyParents).length === 0) &&
                  <TableRow>
                    <TableCell colSpan={2}>
                      <Typography className={classes.noParentsOrChildren} variant="body2">No parents</Typography>
                    </TableCell>
                  </TableRow>
                }
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>
        <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
          <Typography variant="h5" className={classes.headingSpacing}>Children</Typography>
          <TableContainer component={({ ...props }) => <Paper elevation={3} {...props} />}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell className={classes.noWrap}>Individual</TableCell>
                  <TableCell className={classes.noWrap}>Fitness</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {genealogyChildren && Object.entries(genealogyChildren).sort(([, childA], [, childB]) => childB.fitness - childA.fitness).map(([childId, child]) =>
                  <TableRow key={childId}>
                    <TableCell className={classes.noWrap}>
                      <Link to={`/individual/${childId}?type=ditef_producer_genetic_individual_positioner&url=${encodeURIComponent(child.url)}`}>{childId}</Link>
                    </TableCell>
                    <TableCell className={classes.noWrap}>{child.fitness ? child.fitness : "N/A"}</TableCell>
                  </TableRow>
                )}
                {(!genealogyChildren || Object.keys(genealogyChildren).length === 0) &&
                  <TableRow>
                    <TableCell colSpan={2}>
                      <Typography className={classes.noParentsOrChildren} variant="body2">No children</Typography>
                    </TableCell>
                  </TableRow>
                }
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>
      </Grid>
    </Container>
  </>;
}
