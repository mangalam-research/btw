/* global chai Promise describe it */
define(["btw/btw_util"], function factory(btwUtil) {
  "use strict";

  var assert = chai.assert;
  var DONE = Promise.resolve(1);

  describe("btwUtil", function btwUtilSuite() {
    describe("biblSuggestionSorter", function biblSuggestionSorterSuite() {
      var biblSuggestionSorter = btwUtil.biblSuggestionSorter;
      it("accepts an empty array", function test() {
        assert.sameMembers(biblSuggestionSorter([]), []);
        return DONE;
      });

      it("sorts first on creators", function test() {
        var initial = [{
          pk: "2",
          creators: "A, B",
          title: "B",
          date: "2",
        }, {
          pk: "3",
          creators: "A, A",
          title: "C",
          date: "3",
        }];
        var expected = [initial[1], initial[0]];

        assert.sameMembers(biblSuggestionSorter(initial), expected);
        assert.sameMembers(biblSuggestionSorter(expected), expected);
        return DONE;
      });

      it("sorts second on title", function test() {
        var initial = [{
          pk: "2",
          creators: "A, A",
          title: "C",
          date: "2",
        }, {
          pk: "3",
          creators: "A, A",
          title: "B",
          date: "3",
        }];
        var expected = [initial[1], initial[0]];

        assert.sameMembers(biblSuggestionSorter(initial), expected);
        assert.sameMembers(biblSuggestionSorter(expected), expected);
        return DONE;
      });

      it("sorts third on date", function test() {
        var initial = [{
          pk: "2",
          creators: "A, A",
          title: "B",
          date: "3",
        }, {
          pk: "3",
          creators: "A, A",
          title: "B",
          date: "2",
        }];
        var expected = [initial[1], initial[0]];

        assert.sameMembers(biblSuggestionSorter(initial), expected);
        assert.sameMembers(biblSuggestionSorter(expected), expected);
        return DONE;
      });

      it("sorts fourth on pk", function test() {
        var initial = [{
          pk: "10",
          creators: "A, A",
          title: "B",
          date: "3",
        }, {
          pk: "1",
          creators: "A, A",
          title: "B",
          date: "3",
        }];
        var expected = [initial[1], initial[0]];

        assert.sameMembers(biblSuggestionSorter(initial), expected);
        assert.sameMembers(biblSuggestionSorter(expected), expected);
        return DONE;
      });

      it("moves primary sources in front of their secondary sources",
         function test() {
           var initial = [{
             pk: "10",
             creators: "A, A",
             title: "B",
             date: "3",
           }, {
             pk: "1",
             creators: "A, A",
             title: "B",
             date: "3",
           }];

           initial.push({
             pk: "1",
             reference_title: "A",
             item: initial[1],
           });

           initial.push({
             pk: "2",
             reference_title: "B",
             item: initial[0],
           });

           var expected = [initial[2], initial[1], initial[3], initial[0]];

           assert.sameMembers(biblSuggestionSorter(initial), expected);
           assert.sameMembers(biblSuggestionSorter(expected), expected);
           return DONE;
         });

      it("sorts primary sources", function test() {
        var initial = [{
          pk: "10",
          creators: "A, A",
          title: "B",
          date: "3",
        }, {
          pk: "1",
          creators: "A, A",
          title: "B",
          date: "3",
        }];

        initial.push({
          pk: "2",
          reference_title: "B",
          item: initial[1],
        });

        initial.push({
          pk: "1",
          reference_title: "A",
          item: initial[1],
        });

        var expected = [initial[3], initial[2], initial[1], initial[0]];

        assert.sameMembers(biblSuggestionSorter(initial), expected);
        assert.sameMembers(biblSuggestionSorter(expected), expected);
        return DONE;
      });

      it("moves primary sources without a secondary source to the front",
         function test() {
           var initial = [{
             pk: "10",
             creators: "A, A",
             title: "B",
             date: "3",
           }, {
             pk: "1",
             creators: "A, A",
             title: "B",
             date: "3",
           }];

           initial.push({
             pk: "2",
             reference_title: "B",
             item: {
               pk: "3",
               creators: "Q, Q",
               title: "Q",
               date: "1111",
             },
           });

           initial.push({
             pk: "1",
             reference_title: "A",
             item: {
               pk: "4",
               creators: "Z",
               title: "Z",
               date: "2222",
             },
           });


           var expected = [initial[3], initial[2], initial[1], initial[0]];

           assert.sameMembers(biblSuggestionSorter(initial), expected);
           assert.sameMembers(biblSuggestionSorter(expected), expected);
           return DONE;
         });
    });
  });
});
