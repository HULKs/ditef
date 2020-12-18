import React, { useState, useEffect, useCallback } from "react";
import {
  Button,
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
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Fab,
} from "@material-ui/core";
import {
  makeStyles,
  useTheme,
} from "@material-ui/core/styles";
import EditIcon from "@material-ui/icons/Edit";
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
  AreaSeries,
  Legend,
} from '@devexpress/dx-react-chart-material-ui';
import {
  useParams,
} from "react-router-dom";
import { scaleLinear, scaleTime } from "d3-scale";
import {
  Link,
} from "react-router-dom";
import CodeMirror from "@uiw/react-codemirror";
import "./codemirror.css";

import useWebSocket from "../hooks/useWebSocket";

const useStyles = makeStyles(theme => ({
  chartHeadingSpacing: {
    marginTop: theme.spacing(0.5),
    marginBottom: theme.spacing(1),
  },
  memberHeadingSpacing: {
    marginTop: theme.spacing(3),
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
  chartLegend: {
    marginLeft: theme.spacing(1.5),
  },
  noWrap: {
    whiteSpace: "nowrap",
  },
  noMembers: {
    textAlign: "center",
    fontStyle: "italic",
  },
  lastContainer: {
    marginBottom: theme.spacing(4),
  },
}));

export default function Population({ onConnectedChange }) {
  const classes = useStyles();
  const theme = useTheme();
  const { populationId } = useParams();
  const [detailedMetrics, setCurrentMetrics] = useState();
  const [configuration, setConfiguration] = useState();
  const [individualType, setIndividualType] = useState();
  const [members, setMembers] = useState();
  const onWebSocketMessage = useCallback((type, payload) => {
    switch (type) {
      case "configuration": {
        setConfiguration(JSON.stringify(payload, null, 2));
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
  }, []);
  const [connected, error, send] = useWebSocket(
    typeof populationId === "string",
    `ws://${window.location.host}/genetic_algorithm_sliding/api/population/${populationId}/ws/`,
    onWebSocketMessage,
  );
  const [currentConfiguration, setCurrentConfiguration] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const individualString = individualType ? individualType.substring('ditef_producer_genetic_individual_'.length).charAt(0).toUpperCase() + individualType.substring('ditef_producer_genetic_individual_'.length).slice(1) : "";

  useEffect(() => {
    setCurrentConfiguration(configuration);
  }, [configuration]);

  useEffect(() => {
    onConnectedChange(connected);
  }, [onConnectedChange, connected]);

  if (error) {
    return <>Error: {JSON.stringify(error)}</>;
  }

  if (!detailedMetrics || !configuration || !individualType || !members) {
    return <Typography>Loading...</Typography>;
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
    <Fab
      color="primary"
      className={classes.floatingActionButton}
      onClick={() => setDialogOpen(true)}
    >
      <EditIcon />
    </Fab>
    <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
      <DialogTitle>Update configuration</DialogTitle>
      <DialogContent>
        <CodeMirror className={classes.editor} value={currentConfiguration} onChanges={editor => setCurrentConfiguration(editor.getValue())} options={{ mode: "json" }} />
      </DialogContent>
      <DialogActions>
        <Button className={classes.leftButton} onClick={() => setCurrentConfiguration(configuration)}>Reset</Button>
        <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
        <Button onClick={() => { setDialogOpen(false); send("update_configuration", { configuration: JSON.parse(currentConfiguration) }); }}>Update</Button>
      </DialogActions>
    </Dialog>
    <Container>
      <Grid container spacing={2}>
        <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
          <Typography variant="h5" className={classes.chartHeadingSpacing}>Size</Typography>
          <Paper elevation={3}>
            <Chart data={detailedMetricsHistory} height={theme.spacing(30)}>
              <ValueScale factory={scaleLinear} />
              <ArgumentScale factory={scaleTime} />
              <ArgumentAxis showGrid />
              <ValueAxis />
              <LineSeries name="Total" valueField="amount_of_members" argumentField="timestamp" />
              <AreaSeries name="Evaluated" valueField="amount_of_evaluated_members" argumentField="timestamp" />
              <AreaSeries name="Unevaluated" valueField="amount_of_unevaluated_members" argumentField="timestamp" />
              <Legend
                rootComponent={({ children }) => <div className={classes.chartLegend}>{children}</div>}
                itemComponent={({ children }) => <Grid container spacing={1}>{children.map((child, index) => <Grid item key={index}>{child}</Grid>)}</Grid>}
                markerComponent={({ color }) => <svg fill={color} width={theme.spacing(1)} height={theme.spacing(1)}><circle r={theme.spacing(1) / 2} cx={theme.spacing(1) / 2} cy={theme.spacing(1) / 2} /></svg>}
                labelComponent={({ text }) => <Typography variant="body2">{text}</Typography>}
              />
              <Stack stacks={[{ series: ["Evaluated", "Unevaluated"] }]} />
            </Chart>
          </Paper>
        </Grid>
        <Grid item xs={6} sm={6} md={6} lg={6} xl={6}>
          <Typography variant="h5" className={classes.chartHeadingSpacing}>Fitness</Typography>
          <Paper elevation={3}>
            <Chart data={detailedMetricsHistory} height={theme.spacing(30)}>
              <ValueScale factory={scaleLinear} />
              <ArgumentScale factory={scaleTime} />
              <ArgumentAxis showGrid />
              <ValueAxis />
              <LineSeries name="Minimum" valueField="fitness_minimum" argumentField="timestamp" />
              <LineSeries name="Maximum" valueField="fitness_maximum" argumentField="timestamp" />
              <LineSeries name="Std. dev." valueField="fitness_standard_deviation" argumentField="timestamp" />
              <LineSeries name="Mean" valueField="fitness_mean" argumentField="timestamp" />
              <LineSeries name="Median" valueField="fitness_median" argumentField="timestamp" />
              <Legend
                rootComponent={({ children }) => <div className={classes.chartLegend}>{children}</div>}
                itemComponent={({ children }) => <Grid container spacing={1}>{children.map((child, index) => <Grid item key={index}>{child}</Grid>)}</Grid>}
                markerComponent={({ color }) => <svg fill={color} width={theme.spacing(1)} height={theme.spacing(1)}><circle r={theme.spacing(1) / 2} cx={theme.spacing(1) / 2} cy={theme.spacing(1) / 2} /></svg>}
                labelComponent={({ text }) => <Typography variant="body2">{text}</Typography>}
              />
            </Chart>
          </Paper>
        </Grid>
      </Grid>
    </Container>
    <Container className={classes.lastContainer}>
      <Typography variant="h5" className={classes.memberHeadingSpacing}>Members</Typography>
      <TableContainer component={({ ...props }) => <Paper elevation={3} {...props} />}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell className={classes.noWrap}>{individualString} Individual</TableCell>
              <TableCell className={classes.noWrap}>Fitness</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(members).sort(([, memberA], [, memberB]) => memberB.fitness - memberA.fitness).map(([memberId, member]) =>
              <TableRow key={memberId}>
                <TableCell className={classes.noWrap}>
                  <Link to={`/individual/${memberId}?type=${encodeURIComponent(individualType)}&url=${encodeURIComponent(member.url)}`}>{memberId}</Link>
                </TableCell>
                <TableCell className={classes.noWrap}>{member.fitness === null ? "waiting for evaluation" :member.fitness}</TableCell>
              </TableRow>
            )}
            {Object.keys(members).length === 0 &&
              <TableRow>
                <TableCell colSpan={2}>
                  <Typography className={classes.noMembers} variant="body2">No members</Typography>
                </TableCell>
              </TableRow>
            }
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  </>;
}
