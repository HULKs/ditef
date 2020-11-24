import React from "react";
import {
  Typography,
} from "@material-ui/core";
import {
  BrowserRouter,
  Switch,
  Route,
} from "react-router-dom";

import PopulationList from "./PopulationList";
import Population from "./Population";
import Individual from "./Individual";

export default function App() {
  return <BrowserRouter>
    <Typography variant="h1">Sliding Genetic Algorithm</Typography>
    <Switch>
      <Route path="/individual/:individualId">
        <Individual />
      </Route>
      <Route path="/population/:populationId">
        <Population />
      </Route>
      <Route path="/">
        <PopulationList />
      </Route>
    </Switch>
  </BrowserRouter>;
}
