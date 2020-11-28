import React from "react";
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
