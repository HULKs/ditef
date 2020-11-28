import React, { useState } from "react";
import {
  Container,
  Grid,
  Typography,
} from "@material-ui/core";
import { makeStyles } from "@material-ui/core/styles";
import CheckIcon from '@material-ui/icons/Check';
import WarningIcon from '@material-ui/icons/Warning';
import {
  BrowserRouter,
  Switch,
  Route,
  Link,
} from "react-router-dom";

import PopulationList from "./PopulationList";
import Population from "./Population";
import Individual from "./Individual";

const useStyles = makeStyles(theme => ({
  headingSpacing: {
    marginTop: theme.spacing(2),
  },
  headingLink: {
    textDecoration: "inherit",
    color: "inherit",
  },
}));

export default function App() {
  const classes = useStyles();
  const [connected, setConnected] = useState(false);
  
  return <BrowserRouter>
    <Container className={classes.headingSpacing}>
      <Grid container spacing={2} alignItems="baseline">
        <Grid item>
          <Typography variant="h3"><Link to="/" className={classes.headingLink}>Sliding Genetic Algorithm</Link></Typography>
        </Grid>
        <Grid item>
          {connected ? <CheckIcon /> : <WarningIcon />}
        </Grid>
      </Grid>
    </Container>
    <Switch>
      <Route path="/individual/:individualId">
        <Individual onConnectedChange={setConnected} />
      </Route>
      <Route path="/population/:populationId">
        <Population onConnectedChange={setConnected} />
      </Route>
      <Route path="/">
        <PopulationList onConnectedChange={setConnected} />
      </Route>
    </Switch>
  </BrowserRouter>;
}
