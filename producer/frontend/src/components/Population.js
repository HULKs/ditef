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
} from "react-router-dom";
import { scaleLinear, scaleTime } from "d3-scale";
import { timeSecond } from "d3-time";
import {
  Link,
} from "react-router-dom";

import useWebSocket from "../hooks/useWebSocket";

// const useStyles = makeStyles({
//   operationsCell: {
//     whiteSpace: "nowrap",
//   },
// });

export default function PopulationList({ onConnectedChange }) {
  // const classes = useStyles();
  const { populationId } = useParams();
  const [detailedMetrics, setCurrentMetrics] = useState();
  const [configuration, setConfiguration] = useState();
  const [individualType, setIndividualType] = useState();
  const [members, setMembers] = useState();
  const [connected, error, send] = useWebSocket(
    typeof populationId === "string",
    `ws://localhost:8081/genetic_algorithm_sliding/api/population/${populationId}/ws/`,
    (type, payload) => {
      switch (type) {
        case "configuration": {
          setConfiguration(payload);
          break;
        }
        case "detailed_metrics": {
          setCurrentMetrics(payload);
          break;
        }
        case "individual_type": {
          setIndividualType(payload);
          break;
        }
        case "members": {
          setMembers(payload);
          break;
        }
        default: {
          console.warn(`Message type ${type} not implemented.`);
          break;
        }
      }
    },
  );
  const [currentConfiguration, setCurrentConfiguration] = useState("");

  useEffect(() => {
    setCurrentConfiguration(configuration);
  }, [configuration]);

  useEffect(() => {
    onConnectedChange(connected);
  }, [connected]);

  if (error) {
    return <>Error: {JSON.stringify(error)}</>;
  }

  const header = <>
    <Typography variant="body1">{connected ? "Connected" : "Disconnected"}</Typography>
    <Typography variant="h2">Population {populationId}</Typography>
  </>;

  if (!detailedMetrics || !configuration || !individualType || !members) {
    return header;
  }

  const detailedMetricsHistory = detailedMetrics.history.data.map(item =>
    item.reduce((values, current, index) => ({
      ...values,
      [detailedMetrics.history.columns[index]]: current,
    }), {})).map(item => ({
      ...item,
      timestamp: (new Date(item.timestamp)).getTime(),
    }));

  return <>
    {header}
    {individualType}
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Individual</TableCell>
            <TableCell>Fitness</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {Object.entries(members).sort(([memberIdA, memberA], [memberIdB, memberB]) => memberB.fitness - memberA.fitness).map(([memberId, member]) =>
            <TableRow key={memberId}>
              <TableCell>
                <Link to={`/individual/${memberId}?type=${encodeURIComponent(individualType)}&url=${encodeURIComponent(member.url)}`}>Open {memberId}</Link>
              </TableCell>
              <TableCell>{member.fitness ? member.fitness : "N/A"}</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
    <Chart data={detailedMetricsHistory}>
      <ValueScale factory={scaleLinear} />
      <ArgumentScale factory={scaleTime} />
      <ArgumentAxis showGrid />
      <ValueAxis />
      <LineSeries name="Total" valueField="amount_of_members" argumentField="timestamp" />
      <AreaSeries name="Evaluated" valueField="amount_of_evaluated_members" argumentField="timestamp" />
      <AreaSeries name="Unevaluated" valueField="amount_of_unevaluated_members" argumentField="timestamp" />
      <Legend />
      <Title text="Amount of members" />
      <Stack stacks={[{ series: ["Evaluated", "Unevaluated"] }]} />
    </Chart>
    <Chart data={detailedMetricsHistory}>
      <ValueScale factory={scaleLinear} />
      <ArgumentScale factory={scaleTime} />
      <ArgumentAxis showGrid />
      <ValueAxis />
      <LineSeries name="Minimum fitness" valueField="fitness_minimum" argumentField="timestamp" />
      <LineSeries name="Maximum fitness" valueField="fitness_maximum" argumentField="timestamp" />
      <LineSeries name="Median fitness" valueField="fitness_median" argumentField="timestamp" />
      <LineSeries name="Mean fitness" valueField="fitness_mean" argumentField="timestamp" />
      <LineSeries name="Fitness standard deviation" valueField="fitness_standard_deviation" argumentField="timestamp" />
      <Legend />
      <Title text="Fitness" />
    </Chart>
    <TextField variant="outlined" margin="normal" multiline fullWidth value={currentConfiguration} onChange={event => setCurrentConfiguration(event.target.value)} />
    <Button onClick={() => send("update_configuration", { configuration: currentConfiguration })}>Update</Button>
    <Button onClick={() => setCurrentConfiguration(configuration)}>Reset</Button>
  </>;
}
