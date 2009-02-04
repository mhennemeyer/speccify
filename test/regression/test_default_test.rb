require File.dirname(__FILE__) + "/../test_helper.rb"

class MyTestCase < Test::Unit::TestCase
  def hello
    "hello"
  end
end

describe "Custom TestCase", :type => MyTestCase do
  it "says hello" do
    hello.should == "hello"
  end
end

describe "default test" do
  
  def test_a_thing
    #1.should == 1
  end
  
  it "a" do
    1.should == 1
  end
end