"""
Customised authorization for the ecportal extension.
"""

from ckan.lib.base import _
import ckan.logic.auth as ckan_auth

def package_update(context, data_dict):
    """
    Customised package_update auth overrides default ckan behaviour.

    Packages that have been imported by the RDF importer should not be edited
    via the web interface.  But obviously, they need to be updateable via the
    API.

    RDF-imported packages are identified by having an 'rdf' field.
    """
    authorised_by_core = ckan_auth.update.package_update(context, data_dict)
    if authorised_by_core['success'] is False:
        return authorised_by_core
    elif 'api_version' in context:
        return authorised_by_core
    else:
        package = ckan_auth.get_package_object(context, data_dict)
        if 'rdf' in package.extras:
            return {
                'success': False,
                'msg': _('Not authorized to edit RDF-imported datasets by hand.  '
                         'Please re-import this dataset instead.')
            }
        else:
            return authorised_by_core

def show_package_edit_button(context, data_dict):
    """
    Custom ecportal auth function.

    This auth function is only used in one place: on the package layout
    template.  Its sole purpose is to determine whether to display the edit
    button for a given package.  This is determined by the core (default) ckan
    auth layer.  This allows the edit button to be displayed for RDF-imported
    datasets, even though the user won't have the rights to edit an
    RDF-imported dataset (see `package_update` auth above).  This allows the
    edit button to be displayed, but de-activated: giving the user feedback
    on how to update the dataset (ie - re-running the import).
    """
    return ckan_auth.update.package_update(context, data_dict)