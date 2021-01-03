import React, { useState, useEffect, useCallback } from "react";
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
  const [individualType, setIndividualType] = useState();
  const [initialConfiguration, setInitialConfiguration] = useState();
  const [currentMetrics, setCurrentMetrics] = useState();
  const onWebSocketMessage = useCallback((type, payload) => {
    switch (type) {
      case "individual_type": {
        setIndividualType(payload);
        break;
      }
      case "initial_configuration": {
        setInitialConfiguration(JSON.stringify(payload, null, 2));
        break;
      }
      case "current_metrics": {
        setCurrentMetrics(payload);
        break;
      }
      default: {
        console.warn(`Message type ${type} not implemented.`);
        break;
      }
    }
  }, []);
  const [connected, error, send] = useWebSocket(
    true,
    `ws://${window.location.host}/genetic_algorithm_sliding/api/populations/ws/`,
    onWebSocketMessage,
  );
  const [configuration, setConfiguration] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const individualString = individualType ? ('"' + individualType.substring('ditef_producer_genetic_individual_'.length) + '"') : "";

  useEffect(() => {
    setConfiguration(initialConfiguration);
  }, [initialConfiguration]);

  useEffect(() => {
    onConnectedChange(connected);
  }, [onConnectedChange, connected]);

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
        <CodeMirror className={classes.editor} value={configuration} onChanges={editor => setConfiguration(editor.getValue())} options={{ mode: "json" }} />
      </DialogContent>
      <DialogActions>
        <Button className={classes.leftButton} onClick={() => setConfiguration(initialConfiguration)}>Reset</Button>
        <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
        <Button onClick={() => { setDialogOpen(false); send("add_population", { configuration: JSON.parse(configuration) }); }}>Add</Button>
      </DialogActions>
    </Dialog>
    <Container className={classes.lastContainer}>
<Typography variant="h5" className={classes.headingSpacing}>{individualString} populations after {currentMetrics && currentMetrics.length > 0 && currentMetrics[0].total_individuals} individuals born</Typography>
      <TableContainer component={({ ...props }) => <Paper elevation={3} {...props} />}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell className={classes.noWrap}></TableCell>
              <TableCell className={classes.noWrap}>Population type</TableCell>
              <TableCell className={classes.noWrap}>#evaluated</TableCell>
              <TableCell className={classes.noWrap}>Median/Maximum</TableCell>
              <TableCell className={classes.noWrap}>Operations</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {currentMetrics && currentMetrics.map((populationMetrics, populationId) =>
              <TableRow key={populationId}>
                <TableCell className={classes.noWrap}>
                  <Link to={`/population/${populationId}`}>{populationId}</Link>
                </TableCell>
                <TableCell className={classes.noWrap}>"{populationMetrics.type}"</TableCell>
                <TableCell className={classes.noWrap}>{populationMetrics.amount_of_evaluated_members} / {populationMetrics.amount_of_members}</TableCell>
                <TableCell className={classes.noWrap}>
                  {populationMetrics.fitness_median === null ? 'waiting' : populationMetrics.fitness_median.toFixed(4)}
                  /
                  {populationMetrics.fitness_maximum === null ? 'waiting' : populationMetrics.fitness_maximum.toFixed(4)}
                </TableCell>
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
