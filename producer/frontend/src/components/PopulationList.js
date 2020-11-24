import React, { useState, useEffect } from "react";
import {
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@material-ui/core";
import { makeStyles } from "@material-ui/styles";
import {
  Link,
} from "react-router-dom";

import useWebSocket from "../hooks/useWebSocket";

const useStyles = makeStyles({
  operationsCell: {
    whiteSpace: "nowrap",
  },
});

export default function PopulationList() {
  const classes = useStyles();
  const [initialConfiguration, setInitialConfiguration] = useState();
  const [currentMetrics, setCurrentMetrics] = useState();
  const [connected, error, send] = useWebSocket(
    true,
    "ws://localhost:8081/genetic_algorithm_sliding/api/populations/ws/",
    (type, payload) => {
      switch (type) {
        case 'initial_configuration': {
          setInitialConfiguration(payload);
          break;
        }
        case 'current_metrics': {
          setCurrentMetrics(payload);
          break;
        }
        default: {
          console.warn(`Message type ${type} not implemented.`);
          break;
        }
      }
    },
  );
  const [configuration, setConfiguration] = useState("");

  useEffect(() => {
    setConfiguration(initialConfiguration);
  }, [initialConfiguration]);

  if (error) {
    return <>Error: {JSON.stringify(error)}</>;
  }

  // console.log(currentMetrics);
  return <>
    <Typography variant="body1">{connected ? "Connected" : "Disconnected"}</Typography>
    <Typography variant="h2">Populations</Typography>
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Population</TableCell>
            <TableCell>#total</TableCell>
            <TableCell>#evaluated</TableCell>
            <TableCell>#unevaluated</TableCell>
            <TableCell>Minimum fitness</TableCell>
            <TableCell>Maximum fitness</TableCell>
            <TableCell>Median fitness</TableCell>
            <TableCell>Mean fitness</TableCell>
            <TableCell>Fitness standard deviation</TableCell>
            <TableCell>Operations</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {currentMetrics && currentMetrics.map((populationMetrics, populationId) =>
            <TableRow key={populationId}>
              <TableCell>
                <Link to={`/population/${populationId}`}>Open {populationId}</Link>
              </TableCell>
              <TableCell>{populationMetrics.amount_of_members}</TableCell>
              <TableCell>{populationMetrics.amount_of_evaluated_members}</TableCell>
              <TableCell>{populationMetrics.amount_of_unevaluated_members}</TableCell>
              <TableCell>{populationMetrics.fitness_minimum ? populationMetrics.fitness_minimum.toFixed(2) : "N/A"}</TableCell>
              <TableCell>{populationMetrics.fitness_maximum ? populationMetrics.fitness_maximum.toFixed(2) : "N/A"}</TableCell>
              <TableCell>{populationMetrics.fitness_median ? populationMetrics.fitness_median.toFixed(2) : "N/A"}</TableCell>
              <TableCell>{populationMetrics.fitness_mean ? populationMetrics.fitness_mean.toFixed(2) : "N/A"}</TableCell>
              <TableCell>{populationMetrics.fitness_standard_deviation ? populationMetrics.fitness_standard_deviation.toFixed(2) : "N/A"}</TableCell>
              <TableCell className={classes.operationsCell}>
                <Button onClick={() => send("remove_population", { population_index: populationId })}>Remove</Button>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
    <TextField variant="outlined" margin="normal" multiline fullWidth value={configuration} onChange={event => setConfiguration(event.target.value)} />
    <Button onClick={() => send("add_population", { configuration: configuration })}>Add</Button>
  </>;
}
