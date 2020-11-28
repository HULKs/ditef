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
import { makeStyles } from "@material-ui/core/styles";
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

import BitvectorIndividual from "./individuals/BitvectorIndividual";

function useQuery() {
  return new URLSearchParams(useLocation().search);
}

export default function Individual({ onConnectedChange }) {
  const { individualId } = useParams();
  const query = useQuery();
  const type = query.get("type");
  const url = query.get("url");

  if (!type || !url) {
    return <>Loading...</>;
  }

  switch (type) {
    case "ditef_producer_genetic_individual_bitvector": {
      return <BitvectorIndividual individualId={individualId} url={url} onConnectedChange={onConnectedChange} />;
    }
    default: {
      return <>Unknown individual type "{type}"</>;
    }
  }
}
