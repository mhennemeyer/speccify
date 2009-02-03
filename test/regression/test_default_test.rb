require File.dirname(__FILE__) + "/../test_helper.rb"

class MyTestCase < Test::Unit::TestCase
end

describe "With custom TestCase", :type => MyTestCase do
end

describe "default test" do
  
  def test_a_thing
    #1.should == 1
  end
  
  it "a" do
    1.should == 1
  end
end