import React, { useState, useEffect } from "react";
import {
  Button,
  Container,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Fab,
} from "@material-ui/core";
import { makeStyles } from "@material-ui/core/styles";
import AddIcon from "@material-ui/icons/Add";
import {
  Link,
} from "react-router-dom";
import CodeMirror from "@uiw/react-codemirror";
import "./codemirror.css";

import useWebSocket from "../hooks/useWebSocket";

const useStyles = makeStyles(theme => ({
  noWrap: {
    whiteSpace: "nowrap",
  },
  headingSpacing: {
    marginTop: theme.spacing(2),
    marginBottom: theme.spacing(2),
  },
  floatingActionButton: {
    zIndex: (theme.zIndex.appBar + theme.zIndex.drawer) / 2,
    position: "fixed",
    right: theme.spacing(4),
    bottom: theme.spacing(4),
  },
  leftButton: {
    marginRight: "auto",
  },
  noPopulations: {
    textAlign: "center",
    fontStyle: "italic",
  },
  editor: {
    fontFamily: "JetBrains Mono",
  },
  lastContainer: {
    marginBottom: theme.spacing(4),
  },
}));

export default function PopulationList({ onConnectedChange }) {
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
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    setConfiguration(initialConfiguration);
  }, [initialConfiguration]);

  useEffect(() => {
    onConnectedChange(connected);
  }, [connected]);

  if (error) {
    return <Typography>Error: {JSON.stringify(error)}</Typography>;
  }

  return <>
    <Fab
      color="primary"
      className={classes.floatingActionButton}
      onClick={() => setDialogOpen(true)}
    >
      <AddIcon />
    </Fab>
    <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
      <DialogTitle>Add population</DialogTitle>
      <DialogContent>
        <CodeMirror className={classes.editor} value={configuration} onChanges={editor => setConfiguration(editor.getValue())} options={{ mode: "yaml" }} />
      </DialogContent>
      <DialogActions>
        <Button className={classes.leftButton} onClick={() => setConfiguration(initialConfiguration)}>Reset</Button>
        <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
        <Button onClick={() => { setDialogOpen(false); send("add_population", { configuration: configuration }); }}>Add</Button>
      </DialogActions>
    </Dialog>
    <Container className={classes.lastContainer}>
      <Typography variant="h5" className={classes.headingSpacing}>Populations</Typography>
      <TableContainer component={({ ...props }) => <Paper elevation={3} {...props} />}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell className={classes.noWrap}>Population</TableCell>
              <TableCell className={classes.noWrap}>#total</TableCell>
              <TableCell className={classes.noWrap}>#evaluated</TableCell>
              <TableCell className={classes.noWrap}>#unevaluated</TableCell>
              <TableCell className={classes.noWrap}>Minimum fitness</TableCell>
              <TableCell className={classes.noWrap}>Maximum fitness</TableCell>
              <TableCell className={classes.noWrap}>Median fitness</TableCell>
              <TableCell className={classes.noWrap}>Mean fitness</TableCell>
              <TableCell className={classes.noWrap}>Fitness standard deviation</TableCell>
              <TableCell className={classes.noWrap}>Operations</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {currentMetrics && currentMetrics.map((populationMetrics, populationId) =>
              <TableRow key={populationId}>
                <TableCell className={classes.noWrap}>
                  <Link to={`/population/${populationId}`}>Open {populationId}</Link>
                </TableCell>
                <TableCell className={classes.noWrap}>{populationMetrics.amount_of_members}</TableCell>
                <TableCell className={classes.noWrap}>{populationMetrics.amount_of_evaluated_members}</TableCell>
                <TableCell className={classes.noWrap}>{populationMetrics.amount_of_unevaluated_members}</TableCell>
                <TableCell className={classes.noWrap}>{populationMetrics.fitness_minimum ? populationMetrics.fitness_minimum.toFixed(2) : "N/A"}</TableCell>
                <TableCell className={classes.noWrap}>{populationMetrics.fitness_maximum ? populationMetrics.fitness_maximum.toFixed(2) : "N/A"}</TableCell>
                <TableCell className={classes.noWrap}>{populationMetrics.fitness_median ? populationMetrics.fitness_median.toFixed(2) : "N/A"}</TableCell>
                <TableCell className={classes.noWrap}>{populationMetrics.fitness_mean ? populationMetrics.fitness_mean.toFixed(2) : "N/A"}</TableCell>
                <TableCell className={classes.noWrap}>{populationMetrics.fitness_standard_deviation ? populationMetrics.fitness_standard_deviation.toFixed(2) : "N/A"}</TableCell>
                <TableCell className={classes.noWrap}>
                  <Button onClick={() => send("remove_population", { population_index: populationId })}>Remove</Button>
                </TableCell>
              </TableRow>
            )}
            {(!currentMetrics || currentMetrics.length === 0) &&
              <TableRow>
                <TableCell colSpan={10}>
                  <Typography className={classes.noPopulations} variant="body2">No populations</Typography>
                </TableCell>
              </TableRow>
            }
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  </>;
}
