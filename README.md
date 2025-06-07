# FastAPI Filter and Sort

This project is a FastAPI application that demonstrates filtering and sorting functionality for API endpoints.

## Features

- Filtering data based on query parameters
- Sorting data based on query parameters
- Easy to extend and customize

## Requirements

- Python 3.10+
- FastAPI
- SQLAlchemy
- Uvicorn
- Poetry

## Setup

1. Clone the repository:
    ```sh
    git clone https://github.com/bhadri01/fastapi-filter-sort.git
    cd fastapi-filter-sort
    ```
2. Create a virtual environment:
    ```sh
    python -m venv .venv
    . .venv/bin/activate
    ```

3. Install Poetry if you haven't already:
    ```sh
    pip install poetry
    ```

4. Install the dependencies:
    ```sh
    poetry lock
    poetry install
    ```

5. Run the application:
    ```sh
    poetry run python examples/main.py
    ```

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/branch-name`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature/branch-name`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License.
