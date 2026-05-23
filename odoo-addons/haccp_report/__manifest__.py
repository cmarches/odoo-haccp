{
    'name': 'Rapport HACCP DDPP',
    'version': '19.0.1.0.0',
    'summary': 'Rapport PDF réglementaire HACCP pour contrôles DDPP',
    'category': 'Quality',
    'author': 'AIFluence Digital',
    'depends': ['quality_control', 'web', 'mail'],
    # NOTE: requires Odoo Enterprise (quality_control module). Not compatible with Community Edition.
    'data': [
        'security/ir.model.access.csv',
        'report/report_action.xml',
        'report/report_template.xml',
        'views/haccp_report_views.xml',
        'views/haccp_calculs_views.xml',
        'views/haccp_document_views.xml',
        'views/menu.xml',
        'views/quality_inherit.xml',
    ],
    'demo': [
        'demo/haccp_document_demo.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
