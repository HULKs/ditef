import React from "react";
import {
  Typography,
} from "@material-ui/core";
import {
  useParams,
  useLocation,
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
    return <Typography>Loading...</Typography>;
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
