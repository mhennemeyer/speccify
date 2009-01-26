require File.dirname(__FILE__) + "/../test_helper.rb"

describe "def_matcher" do
  
  it "let you call msgs on given" do
    def_matcher :have do |given, matcher, args|
      number = given.send(matcher.fn[0].name).length
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
  
  describe "matcher" do
    it "provides first msg that it has received as fn[0]" do
      def_matcher :matcher_name do |given, matcher, args|
        $fn_name, $fn_args, $fn_block = matcher.fn[0].name, matcher.fn[0].args, matcher.fn[0].block
        true
      end
      1.should matcher_name.msg(1,2,3) {"block"}
      $fn_name.should == :msg
      $fn_args.should == [1,2,3]
      $fn_block.call.should == "block"
    end

    it "provides second msg that it has received as fn[1]" do
      def_matcher :matcher_name do |given, matcher, args|
        $fn_name, $fn_args, $fn_block = matcher.fn[1].name, matcher.fn[1].args, matcher.fn[1].block
        true
      end
      1.should matcher_name.msg1.msg2(1,2,3) {"block"}
      $fn_name.should == :msg2
      $fn_args.should == [1,2,3]
      $fn_block.call.should == "block"
    end
  end
end