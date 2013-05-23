# -*- coding: utf8 -*-

import ckan.controllers.user
import ckan.model as model
import ckan.plugins as p
import ckan.lib.navl.dictization_functions
import ckan.lib.helpers
import ckanext.ecportal.schema as schema
import forms
import sqlalchemy.exc
import datetime
from ckan.lib.base import request, c, BaseController, model, abort, h, g, render, response, _, json
from ckan.controllers.home import HomeController
import ckanext.ecportal.searchcloud as searchcloud
import ckanext.ecportal.mostviewed as mostviewed
import logging
log = logging.getLogger(__name__)

class SearchCloudException(Exception):
    pass

class ECPortalSearchCloudAdminController(BaseController):
    '''
    Allow a sysadmin to download the latest list of terms
    '''
    # Can't do this check in __before__ as c.user is not yet set up
    def _sysadmin_or_abort(self):
        if not c.user:
            return abort(401, _('Not signed in'))
        is_admin = self.authorizer.is_sysadmin(c.user)
        if not is_admin:
            return abort(
                401,
                _('You are not authorized to access search cloud administation')
            )

    def index(self):
        self._sysadmin_or_abort()
        return render('searchcloud/index.html')

    def _parse_json(self, json_data):
        try:
            rows = json.loads(json_data)
        except:
            raise SearchCloudException(
                'JSON file could not be parsed. Please ensure file is valid'
                ' JSON and pay careful attention to trailing commas.'
            )
        else:
            values = []
            if not isinstance(rows, list):
                raise SearchCloudException(
                    'JSON file does not contain a list of terms. Expected the'
                    ' same format as the download.'
                )
            for i, row in enumerate(rows):
                if not isinstance(row, list):
                    raise SearchCloudException(
                        (
                        'Row %i has a value %r. It is not a list of'
                        ' [search_string, count]. Expected the same format'
                        ' as the download.'
                        )%(i, row,)
                    )
                try:
                    count = int(row[1])
                except:
                    raise SearchCloudException(
                        'Could not parse the count for row %s'%(i,)
                    )
                else:
                    if not row[0].strip():
                        raise SearchCloudException(
                            "Row %i doesn't contain a search string"%(i,)
                        )
                    values.append([row[0].strip(), count])
            return values 

    def upload(self):
        self._sysadmin_or_abort()
        if request.method == 'GET':
            return render('searchcloud/upload.html')
        else:
            file_field = request.POST['searchcloud']
            data = file_field.value.decode('utf8')
            try:
                rows = self._parse_json(data)
            except SearchCloudException, e:
                c.error = str(e)
                return render('searchcloud/error.html')
            else:
                c.json = searchcloud.approved_to_json(rows)
                c.data = data
                return render('searchcloud/preview.html')

    def save(self):
        self._sysadmin_or_abort()
        data = request.POST['searchcloud']
        try:
            rows = self._parse_json(data)
        except SearchCloudException, e:
            c.error = str(e)
            return render('searchcloud/error.html')
        else:
            searchcloud.update_approved(model.Session, rows)
            # Save our changes
            model.Session.commit()
            return render('searchcloud/saved.html')

    def download(self):
        self._sysadmin_or_abort()
        data = searchcloud.get_latest(model.Session)
        response.charset = 'utf8'
        response.content_type = 'application/json'
        response.headers['Content-Disposition'] = 'attachment; filename="ecodp-searchcloud-latest-%s.json"'%(
            # We don't know when the script is run, so let's assume just
            # after midnight and use today's date
            datetime.datetime.now().strftime( 
                '%Y-%m-%d',
            )
        )
        return json.dumps(data, indent=4)


class ECPortalHomeController(HomeController):
    '''
    Overrides the index() method to add the data needed to render the search
    cloud on the homepage
    '''
    def index(self):
        c.most_viewed_datasets = None
        try:
            rows = mostviewed.get_most_viewed(model.Session, 10)
        except sqlalchemy.exc.ProgrammingError:
            log.error('Could not retrieve most viewed results from database. Do the tables exist? Rolling back the session.')
            model.Session.rollback()
        else:
            if rows:
                c.most_viewed_datasets = rows
        c.json = None 
        try:
            rows = searchcloud.get_approved(model.Session)
        except sqlalchemy.exc.ProgrammingError:
            log.error('Could not retrieve search cloud results from database. Do the tables exist? Rolling back the session.')
            model.Session.rollback()
        else:
            if rows:
                c.json = searchcloud.approved_to_json(rows)
        return HomeController.index(self)



_validate = ckan.lib.navl.dictization_functions.validate
json = ckan.lib.helpers.json
_f = forms.ECPortalDatasetForm()


def _vocabularies(tag_name):
    '''
    Return a list containing the names of each vocabulary that
    contains the tag tag_name.

    Returns an empty list if tag_name does not belong to any vocabulary.

    If no such tag exists, throws a ckan.plugins.toolkit.ObjectNotFound
    exception.
    '''
    query = model.Session.query(model.tag.Tag.name,
                                model.vocabulary.Vocabulary.name)\
        .filter(model.tag.Tag.name == tag_name)\
        .filter(model.tag.Tag.vocabulary_id == model.vocabulary.Vocabulary.id)
    return [t[1] for t in query]


class ECPortalUserController(ckan.controllers.user.UserController):
    '''
    EC Portal User controller is customised to allow customisation of the
    user schema
    '''
    def _edit_form_to_db_schema(self):
        return schema.user_edit_form_schema()

    def _new_form_to_db_schema(self):
        return schema.user_new_form_schema()


class ECPortalDatasetController(p.SingletonPlugin):
    p.implements(p.IPackageController)

    def read(self, entity):
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass

    def before_search(self, search_params):
        return search_params

    def after_search(self, search_results, search_params):
        return search_results

    def before_index(self, pkg_dict):
        # save a validated version of the package dict in the search index
        context = {'model': model,
                   'session': model.Session,
                   'user': u''}
        schema = _f.db_to_form_schema({})

        validated_pkg, errors = _validate(json.loads(pkg_dict['data_dict']),
                                          schema,
                                          context=context)
        pkg_dict['data_dict'] = json.dumps(validated_pkg)

        pkg_dict.pop('rdf', None)
        pkg_dict.pop('extras_rdf', None)

        # remove vocab tags from 'tags' list and add them as vocab_<tag name>
        # so that they can be used in facets
        free_tags = []

        for tag in pkg_dict.get('tags'):
            vocabs = _vocabularies(tag)
            if vocabs:
                for vocab in vocabs:
                    key = u'vocab_%s' % vocab
                    if key in pkg_dict:
                        pkg_dict[key].append(tag)
                    else:
                        pkg_dict[key] = [tag]
            else:
                free_tags.append(tag)

        pkg_dict['tags'] = free_tags

        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict
