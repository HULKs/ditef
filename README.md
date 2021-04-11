# DiTEF - Distributed Task Execution Framework with Genetic Algorithm for Neural Network Architecture Search

## Structure

- `producer/`: all task producer components
  - `backend/`: task producer backend
    - `genetic_algorithm/`: implementation of genetic algorithm as task producer
    - `genetic_individual/`: producer individual implementations
    - `shared/`: code shared between genetic algorithm and individuals
  - `frontend/`: web interface of task producer
- `router/`: central task router implementation
- `worker/`: all task worker components
  - `worker/`: task worker (capable of executing evaluation code of worker individuals)
  - other directories: worker individual implementations (evaluation code)

## Installation

### DiTEF and Genetic Algorithm

The following packages should be installed on a central device/environment:

```bash
pip install --editable producer/backend/genetic_algorithm/sliding/
pip install --editable producer/backend/shared/
pip install --editable router/
yarn install --cwd producer/frontend/
```

The worker may be installed on all devices/environments that should act as workers:

```bash
pip install --editable worker/worker/
```

### Individuals

For each individual type there exists a backend and worker part (the frontend is installed by default). The code can be installed from the following directories (replace `...` with the individual type name):

```bash
pip install --editable producer/backend/genetic_individual/.../
pip install --editable worker/.../
```

**Note:** The directory name is not the individual type. The individual type is contained in the `setup.py` file (`name` field) within each directory.

The worker part of the neural network individual type has Tensorflow as a dependency. You may want to install this in a different environment (e.g. Docker image). We provide shell scripts for building a Docker image (see `worker/genetic_individual_neuralnet/build.sh`).

Custom individuals may be implemented in the aforementioned directories. This repository already contains individuals in `producer/backend/genetic_individual/`.

### Additional Algorithms

Custom algorithms may be implemented and installed from directories in `producer/backend/`.

## Usage

First, start the central task router:

```bash
ditef-router
```

Next, connect at least one task worker to the task router with the following arguments:

1. Router URL, e.g. `http://localhost:8080/`
2. Worker Individual Type (`name` field of `setup.py` in `worker/.../` directory)

For example, for starting a worker for bitvector individual type:

```bash
ditef-worker http://localhost:8080/ ditef_worker_genetic_individual_bitvector
```

Start the sliding genetic algorithm task producer with the following arguments:

1. Router URL, e.g. `http://localhost:8080/`
2. Producer Individual Type (`name` field of `setup.py` in `producer/backend/genetic_individual/.../` directory)
3. Algorithm State Directory (will be created if it doesn't exist)

For example, for starting an algorithm for bitvector individual type:

```bash
ditef-producer-genetic-algorithm-sliding http://localhost:8080/ ditef_producer_genetic_individual_bitvector my_fancy_state
```

Start the frontend:

```bash
cd producer/frontend/
yarn start
```

After these steps, you can connect to the frontend and use the web interface.

## License

MIT
