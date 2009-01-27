require File.dirname(__FILE__) + "/../test_helper.rb"

describe "def_matcher" do
  
  it "let you call msgs on given" do
    def_matcher :have do |given, matcher, args|
      number = given.send(matcher.msgs[0].name).length
      args[0] == number
    end
    class AnswerToMSGWithThreeEltList
      def msg
        [1,2,3]
      end
      self
    end
    AnswerToMSGWithThreeEltList.new.should have(3).msg
  end
  
  describe "matcher" do
    it "provides first msg that it has received as msgs[0]" do
      def_matcher :matcher_name do |given, matcher, args|
        $msg_name, $msg_args, $msg_block = matcher.msgs[0].name, matcher.msgs[0].args, matcher.msgs[0].block
        true
      end
      1.should matcher_name.msg(1,2,3) {"block"}
      $msg_name.should == :msg
      $msg_args.should == [1,2,3]
      $msg_block.call.should == "block"
    end

    it "provides second msg that it has received as msgs[1]" do
      def_matcher :matcher_name do |given, matcher, args|
        $msg_name, $msg_args, $msg_block = matcher.msgs[1].name, matcher.msgs[1].args, matcher.msgs[1].block
        true
      end
      1.should matcher_name.msg1.msg2(1,2,3) {"block2"}
      $msg_name.should == :msg2
      $msg_args.should == [1,2,3]
      $msg_block.call.should == "block2"
    end
  end
end