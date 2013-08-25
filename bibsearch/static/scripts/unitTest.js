require(["modules/testSearch","modules/testSync", "qunit"], function (testbed, testbed2, QUnit) {
            // alert the tester that he/she authenticates to the app for testing ajax
            alert("All tests assume the current django user is authenticated");
            // search experience tests
            QUnit.start();
            testbed.SearchTests();
            // sync experience tests
            alert("Before attempting sync tests, we also need to search\n"+
                  "and get results in results cache");
            testbed2.SyncTests();
            // results view aka paginated results not tested as they are django feature.
        });
