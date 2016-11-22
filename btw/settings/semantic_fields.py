from lib.settings import s

s.PIPELINE["STYLESHEETS"]["semantic_fields"] = {
    'source_filenames': (
        'css/semantic_fields.less',
    ),
    'output_filename': 'css/semantic_fields.css'
}
