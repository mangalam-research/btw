Feature: editing primary sources cannot happen without permission.

Scenario: a user cannot add a primary source without permission.
  Given a user without permission to edit primary sources has logged in
  Then the user does not have the "Bibliography/Manage" navigation option
