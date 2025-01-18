# Releases Notes

## Version 1.0.0 - 2024-12-22
* The term `grant_number` has been added to the entity `Grant`. It reuse the [FRAPO](https://w3id.org/spar/frapo) data property `frapo:hasGrantNumber`.

## Version 0.2.0 - 2024-10-03

* All the keys in the context that contained spaces have been substituted with identical keys where spaces have been replaced by underscores. In particular, we changed the following keys:
  * local identifier -> local_identifier
  * entity type -> entity_type
  * product type -> product_type
  * associated with -> associated_with
  * declared affiliations -> declared_affiliations
  * defined in -> defined_in
  * peer review -> peer_review
  * access rights -> access_rights
  * hosting data source -> hosting_data_source
  * relevant organisations -> relevant_organisations
  * related products -> related_products
  * is supplemented by -> is_supplemented_by
  * is documented by -> is_documented_by
  * is new version of -> is_new_version_of
  * is part of -> is_part_of
  * given name -> given_name
  * family name -> family_name
  * short name -> short_name
  * other names -> other_names
  * creation date -> creation_date
  * documented at -> documented_at
  * persistent identity systems -> persistent_identity_systems
  * pid schemes -> pid_schemes
  * audience type -> audience_type
  * data source classification -> data_source_classification
  * research product type -> research_product_type
  * funding agency -> funding_agency
  * funding stream -> funding_stream
  * funded amount -> funded_amount
* Corrected a few typos in the samples.

## Version 0.1.0 - 2024-09-20

* Published the first version of the JSON-LD context.