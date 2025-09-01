from pathlib import Path


def get_header_footer(filepath: Path,
                      end_header_pattern: str = "begin lectures",
                      end_body_pattern: str = "end lectures"
                      ) -> tuple[str, str, str]:
    """ Copy header and footer from main.tex, includes line with end_(header/footer)_pattern in header and footer respectively
    -- Params --
    filepath: path to file
    end_header_pattern: pattern signaling preamble is terminating in main.tex
    end_body_pattern: pattern signaling last lecture to be included in main.tex
    returns: (header, body, footer)
    """
    part = "header"
    header, footer, body = '', '', ''

    with filepath.open() as f:
        for line in f:
            if end_body_pattern in line:
                part = 'footer'

            if part == 'header':
                header += line

            if part == 'footer':
                footer += line

            if part == "body":
                body += line

            if end_header_pattern in line:
                part = "body"

    return (header, body, footer)
