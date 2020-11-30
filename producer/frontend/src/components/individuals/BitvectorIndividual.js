import React, { useState, useEffect } from "react";
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
import green from "@material-ui/core/colors/green";
import red from "@material-ui/core/colors/red";
import {
  Link,
} from "react-router-dom";

import useWebSocket from "../../hooks/useWebSocket";

const useStyles = makeStyles(theme => ({
  headingSpacing: {
    marginTop: theme.spacing(2),
    marginBottom: theme.spacing(1),
  },
  gene: {
    flexGrow: 0,
    height: theme.spacing(2),
  },
  genomePaper: {
    overflow: "hidden",
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

export default function BitvectorIndividual({ url, onConnectedChange }) {
  const classes = useStyles();
  const [genome, setGenome] = useState();
  const [fitness, setFitness] = useState();
  const [creationType, setCreationType] = useState();
  const [genealogyParents, setGenealogyParents] = useState();
  const [genealogyChildren, setGeneaglogyChildren] = useState();
  const [connected, error,] = useWebSocket(
    true,
    `ws://localhost:8081${url}`,
    (type, payload) => {
      switch (type) {
        case "genome": {
          setGenome(payload);
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
    },
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
      <Typography variant="h5" className={classes.headingSpacing}>Bitvector Genome</Typography>
      <Paper elevation={3} className={classes.genomePaper}>
        <Grid container>
          {genome && genome.map(gene =>
            <Grid className={classes.gene} item style={{ flexGrow: 0, maxWidth: `${100 / genome.length}%`, flexBasis: `${100 / genome.length}%`, backgroundColor: gene ? green[500] : red[500] }}></Grid>
          )}
        </Grid>
      </Paper>
    </Container>
    <Container>
      <Typography variant="h5" className={classes.headingSpacing}>Fitness</Typography>
      <Paper elevation={3} className={classes.fitnessPaper}>
        <Typography className={classes.fitness}>{fitness}</Typography>
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
                      <Link to={`/individual/${parentId}?type=ditef_producer_genetic_individual_bitvector&url=${encodeURIComponent(parent.url)}`}>{parentId}</Link>
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
                      <Link to={`/individual/${childId}?type=ditef_producer_genetic_individual_bitvector&url=${encodeURIComponent(child.url)}`}>{childId}</Link>
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
