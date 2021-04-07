import React from "react";
import {
  Typography,
} from "@material-ui/core";
import {
  useParams,
  useLocation,
} from "react-router-dom";

import BitvectorIndividual from "./individuals/BitvectorIndividual";
import BallDetectionCNNIndividual from "./individuals/BallDetectionCNNIndividual";
import StringIndividual from "./individuals/StringIndividual";

function useQuery() {
  return new URLSearchParams(useLocation().search);
}

export default function Individual({ onConnectedChange }) {
  const { individualId } = useParams();
  const query = useQuery();
  const type = query.get("type");
  const url = query.get("url");

  if (!type || !url) {
    return <Typography>Loading...</Typography>;
  }

  switch (type) {
    case "ditef_producer_genetic_individual_bitvector": {
      return <BitvectorIndividual individualId={individualId} url={url} onConnectedChange={onConnectedChange} />;
    }
    case "ditef_producer_genetic_individual_ball_detection_cnn": {
      return <BallDetectionCNNIndividual individualId={individualId} url={url} onConnectedChange={onConnectedChange} />;
    }
    case "ditef_producer_genetic_individual_string": {
      return <StringIndividual individualId={individualId} url={url} onConnectedChange={onConnectedChange} />;
    }
    default: {
      return <Typography>Unknown individual type &quot;{type}&quot;</Typography>;
    }
  }
}
