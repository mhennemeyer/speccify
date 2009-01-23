require File.dirname(__FILE__) + "/test_helper.rb"

describe "def_matcher" do
  it "yields a matcher object that provides all msgs that it has received as fn attribute" do
    def_matcher :matcher_name do |given, matcher, args|
      $fn_name = matcher.fn.name
      true
    end
    1.should matcher_name.msg
    $fn_name.should == :msg
  end
  
  
  it "let you call msgs on given" do
    def_matcher :have do |given, matcher, args|
      number = given.send(matcher.fn.name).length
      args[0] == number
    end
    class AnswerToWithThreeEltList
      def msg
        [1,2,3]
      end
      self
    end
    AnswerToWithThreeEltList.new.should have(3).msg
  end
end