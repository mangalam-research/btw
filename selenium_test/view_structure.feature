Feature: Articles are properly structured for viewing.
  As a regular user, I want articles that reflect the actual structure of
  the document when I view them.

Scenario: viewing senses and subsenses
  Given a document with senses and subsenses
  Then the senses and subsenses are properly numbered
