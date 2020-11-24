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
  ArgumentScale,
  Stack,
  ValueScale,
} from '@devexpress/dx-react-chart';
import {
  Chart,
  ArgumentAxis,
  ValueAxis,
  LineSeries,
  SplineSeries,
  AreaSeries,
  Title,
  Legend,
} from '@devexpress/dx-react-chart-material-ui';
import {
  useParams,
  useLocation,
} from "react-router-dom";
import { scaleLinear, scaleTime } from "d3-scale";
import { timeSecond } from "d3-time";
import {
  Link,
} from "react-router-dom";

import useWebSocket from "../../hooks/useWebSocket";

// const useStyles = makeStyles({
//   operationsCell: {
//     whiteSpace: "nowrap",
//   },
// });

export default function BitvectorIndividual({ individualId, url }) {
  // const classes = useStyles();
  const [genome, setGenome] = useState();
  const [fitness, setFitness] = useState();
  const [creationType, setCreationType] = useState();
  const [genealogyParents, setGenealogyParents] = useState();
  const [genealogyChildren, setGeneaglogyChildren] = useState();
  const [connected, error, send] = useWebSocket(
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
      }
    },
  );
  
  if (error) {
    return <>Error: {JSON.stringify(error)}</>;
  }

  if (!connected || error) {
    return <>N/A</>;
  }

  return <>
    <div>individualId: {individualId}</div>
    <div>url: {url}</div>
    <div>genome: {JSON.stringify(genome)}</div>
    <div>fitness: {JSON.stringify(fitness)}</div>
    <div>creationType: {JSON.stringify(creationType)}</div>
    <div>genealogyParents: {JSON.stringify(genealogyParents)}</div>
    <div>genealogyChildren: {JSON.stringify(genealogyChildren)}</div>
  </>;
}
