# Copyright (c) 2024-present yowoda
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json
import typing as t

import pytest
from pathlib import Path

from autopep695.analyzer import format_code
from autopep695.errors import ParsingError
from tests.autopep695.util import remove_empty_lines


class TestFormatCode:
    @pytest.fixture(scope="function")
    def path(self) -> Path:
        return Path("")

    def test_parsing_error(self, path: Path):
        code = "1 + "

        with pytest.raises(ParsingError):
            format_code(
                code,
                file_path=path,
            )

    def test_with_data(self):
        for case_path in Path("tests/autopep695/data").iterdir():
            if case_path.is_file():
                continue

            input_path = case_path / "input.py"
            output_path = case_path / "output.py"
            settings_path = case_path / "settings.json"

            if not all(
                (input_path.exists(), output_path.exists(), settings_path.exists())
            ):
                raise RuntimeError(f"{case_path} contains an incomplete testing case.")

            input_code = input_path.read_text(encoding="utf-8").strip()
            expected_output = output_path.read_text(encoding="utf-8").strip()

            with settings_path.open("r") as f:
                settings: dict[str, t.Any] = json.load(f)

            if "format" not in settings:
                raise RuntimeError(
                    f"{settings_path} does not contain `format` configuration"
                )

            if settings.get("ignore_empty_lines", False) is True:
                input_code = remove_empty_lines(input_code)
                expected_output = remove_empty_lines(expected_output)

            parameters = settings["format"]

            assert (
                format_code(input_code, file_path=input_path, **parameters)
                == expected_output
            )
